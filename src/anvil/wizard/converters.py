"""Converters for Anvil evaluation format.

Converts the trading-platform-backend task format to Anvil's evaluation format
which includes:
- instances.yaml - List of instances for run-evals
- gold_patches.json - Reference patches for oracle evaluation
- tasks.csv - Combined CSV of all tasks
- dockerfiles/ - Docker image definitions
- run_scripts/ - Test execution scripts
"""

from __future__ import annotations

import csv
import io
import json
import shutil
from pathlib import Path
from typing import Annotated

import typer
import yaml

from .models import Task, TestSpec
from .templates import PARSER_PY


def _parse_instance_info(instance_info_path: Path) -> dict:
    """Parse instance_info.txt file."""
    content = instance_info_path.read_text()
    result = {}

    for line in content.strip().split("\n"):
        if ": " in line:
            key, value = line.split(": ", 1)
            key = key.strip().lower().replace(" ", "_")
            result[key] = value.strip()

    return result


def _parse_tasks_csv(csv_path: Path) -> dict:
    """Parse tasks.csv file and return the first data row as dict."""
    content = csv_path.read_text()
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        return dict(row)
    return {}


def load_task_from_directory(task_dir: Path) -> Task | None:
    """Load a Task from a task directory.

    Expected files:
    - instance_info.txt
    - tasks.csv
    - task_tests.py
    """
    instance_info_path = task_dir / "instance_info.txt"
    tasks_csv_path = task_dir / "tasks.csv"
    tests_path = task_dir / "task_tests.py"

    if not all(p.exists() for p in [instance_info_path, tasks_csv_path, tests_path]):
        return None

    instance_info = _parse_instance_info(instance_info_path)
    csv_data = _parse_tasks_csv(tasks_csv_path)

    # Parse fail_to_pass and pass_to_pass from instance_info
    fail_to_pass = []
    pass_to_pass = []

    fail_str = instance_info.get("fail_to_pass", "[]")
    pass_str = instance_info.get("pass_to_pass", "[]")

    try:
        fail_to_pass = eval(fail_str) if fail_str else []
    except Exception:
        pass

    try:
        pass_to_pass = eval(pass_str) if pass_str else []
    except Exception:
        pass

    return Task(
        task_id=task_dir.name,
        instance_id=instance_info.get("instance_id", f"{task_dir.parent.name}.{task_dir.name}"),
        problem_statement=csv_data.get("problem_statement", ""),
        patch=csv_data.get("patch", ""),
        test_code=tests_path.read_text(),
        test_spec=TestSpec(fail_to_pass=fail_to_pass, pass_to_pass=pass_to_pass),
        base_commit=csv_data.get("base_commit", ""),
        repo=csv_data.get("repo", ""),
        language=csv_data.get("repo_language", "Python"),
        before_repo_set_cmd=csv_data.get("before_repo_set_cmd", ""),
        requirements=csv_data.get("requirements", ""),
        interface=csv_data.get("interface", ""),
        issue_specificity=csv_data.get("issue_specificity", ""),
        issue_categories=csv_data.get("issue_categories", ""),
    )


def load_all_tasks(dataset_path: Path) -> list[Task]:
    """Load all tasks from a dataset directory."""
    tasks = []

    for item in sorted(dataset_path.iterdir()):
        if item.is_dir() and item.name.startswith("task-"):
            task = load_task_from_directory(item)
            if task:
                tasks.append(task)

    return tasks


def generate_instances_yaml(
    tasks: list[Task],
    dockerhub_username: str,
    dockerhub_repo: str,
    dataset_id: str,
) -> str:
    """Generate instances.yaml content for Anvil's run-evals."""
    instances = []

    for task in tasks:
        # Generate image name: username/repo:dataset.task-N
        image_tag = f"{dataset_id}.{task.task_id}"
        image_name = f"{dockerhub_username}/{dockerhub_repo}:{image_tag}"

        instance = {
            "instance_id": task.instance_id,
            "image_name": image_name,
            "problem_statement": task.problem_statement,
            "before_repo_set_cmd": task.before_repo_set_cmd,
        }
        instances.append(instance)

    return yaml.dump(instances, default_flow_style=False, sort_keys=False)


def generate_gold_patches_json(tasks: list[Task]) -> str:
    """Generate gold_patches.json for oracle evaluation."""
    patches = []

    for task in tasks:
        patch_entry = {
            "instance_id": task.instance_id,
            "patch": task.patch,
            "prefix": "gold",
        }
        patches.append(patch_entry)

    return json.dumps(patches, indent=2)


def generate_combined_tasks_csv(tasks: list[Task]) -> str:
    """Generate combined tasks.csv with all tasks."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Header
    header = [
        "repo", "instance_id", "base_commit", "patch", "test_patch",
        "problem_statement", "requirements", "interface", "repo_language",
        "fail_to_pass", "pass_to_pass", "issue_specificity", "issue_categories",
        "before_repo_set_cmd", "selected_test_files_to_run",
    ]
    writer.writerow(header)

    # Data rows
    for task in tasks:
        row = [
            task.repo,
            task.instance_id,
            task.base_commit,
            task.patch,
            "",  # test_patch
            task.problem_statement,
            task.requirements,
            task.interface,
            task.language,
            str(task.test_spec.fail_to_pass),
            str(task.test_spec.pass_to_pass),
            task.issue_specificity,
            task.issue_categories,
            task.before_repo_set_cmd,
            f"tasks/{task.task_id}/task_tests.py",
        ]
        writer.writerow(row)

    return output.getvalue()


def convert_to_anvil_structure(
    dataset_path: Path,
    output_path: Path,
    dockerhub_username: str,
    dockerhub_repo: str,
) -> dict[str, list[Path]]:
    """Convert trading-platform-backend format to Anvil evaluation format.

    Returns dict of created file paths by category.
    """
    dataset_id = dataset_path.name
    tasks = load_all_tasks(dataset_path)

    if not tasks:
        raise ValueError(f"No tasks found in {dataset_path}")

    created_files: dict[str, list[Path]] = {
        "config": [],
        "dockerfiles": [],
        "run_scripts": [],
    }

    # Create output directories
    output_path.mkdir(parents=True, exist_ok=True)
    dockerfiles_base_dir = output_path / "dockerfiles" / "docker_image_creation" / dataset_id
    dockerfiles_instance_dir = output_path / "dockerfiles" / "instance_dockerfile"
    run_scripts_dir = output_path / "run_scripts"

    dockerfiles_base_dir.mkdir(parents=True, exist_ok=True)
    dockerfiles_instance_dir.mkdir(parents=True, exist_ok=True)
    run_scripts_dir.mkdir(parents=True, exist_ok=True)

    # Copy base Dockerfile
    base_dockerfile = dataset_path / "Dockerfile"
    if base_dockerfile.exists():
        dest = dockerfiles_base_dir / "Dockerfile"
        shutil.copy(base_dockerfile, dest)
        created_files["dockerfiles"].append(dest)

    # Generate instances.yaml
    instances_yaml = generate_instances_yaml(
        tasks, dockerhub_username, dockerhub_repo, dataset_id
    )
    instances_path = output_path / "instances.yaml"
    instances_path.write_text(instances_yaml)
    created_files["config"].append(instances_path)

    # Generate gold_patches.json
    gold_patches = generate_gold_patches_json(tasks)
    gold_patches_path = output_path / "gold_patches.json"
    gold_patches_path.write_text(gold_patches)
    created_files["config"].append(gold_patches_path)

    # Generate combined tasks.csv
    tasks_csv = generate_combined_tasks_csv(tasks)
    tasks_csv_path = output_path / "tasks.csv"
    tasks_csv_path.write_text(tasks_csv)
    created_files["config"].append(tasks_csv_path)

    # Process each task
    for task in tasks:
        # Create instance dockerfile directory
        instance_docker_dir = dockerfiles_instance_dir / task.instance_id
        instance_docker_dir.mkdir(parents=True, exist_ok=True)

        # Copy task Dockerfile
        task_dockerfile = dataset_path / task.task_id / "Dockerfile"
        if task_dockerfile.exists():
            dest = instance_docker_dir / "Dockerfile"
            shutil.copy(task_dockerfile, dest)
            created_files["dockerfiles"].append(dest)

        # Create run_scripts directory for this instance
        instance_scripts_dir = run_scripts_dir / task.instance_id
        instance_scripts_dir.mkdir(parents=True, exist_ok=True)

        # Copy run_script.sh
        run_script = dataset_path / task.task_id / "run_script.sh"
        if run_script.exists():
            dest = instance_scripts_dir / "run_script.sh"
            shutil.copy(run_script, dest)
            dest.chmod(0o755)
            created_files["run_scripts"].append(dest)

        # Copy parser.py
        parser_py = dataset_path / task.task_id / "parser.py"
        if parser_py.exists():
            dest = instance_scripts_dir / "parser.py"
            shutil.copy(parser_py, dest)
            created_files["run_scripts"].append(dest)

        # Copy instance_info.txt
        instance_info = dataset_path / task.task_id / "instance_info.txt"
        if instance_info.exists():
            dest = instance_scripts_dir / "instance_info.txt"
            shutil.copy(instance_info, dest)
            created_files["run_scripts"].append(dest)

    return created_files


def convert_dataset(
    dataset: Annotated[str, typer.Option("--dataset", "-d", help="Dataset path")],
    dockerhub_username: Annotated[
        str, typer.Option("--dockerhub-username", "-u", help="Docker Hub username")
    ] = "afterquery",
    dockerhub_repo: Annotated[
        str, typer.Option("--dockerhub-repo", help="Docker Hub repository name")
    ] = "sweap-images",
    output_dir: Annotated[
        Path | None, typer.Option("--output-dir", "-o", help="Output directory")
    ] = None,
) -> None:
    """Convert dataset to Anvil evaluation format.

    Generates instances.yaml, gold_patches.json, and the directory structure
    required for Anvil's publish-images and run-evals commands.
    """
    # Resolve dataset path
    dataset_path = Path(dataset)
    if not dataset_path.is_absolute():
        dataset_path = Path.cwd() / dataset

    if not dataset_path.exists():
        typer.secho(f"Error: Dataset directory does not exist: {dataset_path}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Determine output directory
    if output_dir:
        output_path = output_dir
    else:
        output_path = dataset_path / "tasks"

    typer.echo(f"Converting dataset {dataset_path.name} to Anvil format...")
    typer.echo(f"Output directory: {output_path}")

    try:
        created_files = convert_to_anvil_structure(
            dataset_path=dataset_path,
            output_path=output_path,
            dockerhub_username=dockerhub_username,
            dockerhub_repo=dockerhub_repo,
        )
    except ValueError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Summary
    typer.secho("\nConversion completed successfully!", fg=typer.colors.GREEN)

    typer.echo("\nCreated files:")
    typer.echo("  Config:")
    for f in created_files["config"]:
        typer.echo(f"    - {f.relative_to(output_path)}")

    typer.echo(f"  Dockerfiles: {len(created_files['dockerfiles'])} files")
    typer.echo(f"  Run scripts: {len(created_files['run_scripts'])} files")

    typer.echo("\nNext steps:")
    typer.echo(f"  1. Publish images: anvil publish-images --dataset {dataset_path}")
    typer.echo(f"  2. Run evaluation: anvil run-evals --dataset {dataset_path} --agent oracle")
