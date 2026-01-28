"""File content generators for task creation."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from .models import Dataset, Task
from .templates import (
    BASE_DOCKERFILE_TEMPLATE,
    INSTANCE_INFO_TEMPLATE,
    PARSER_PY,
    REQUIREMENTS_TXT,
    RUN_SCRIPT_TEMPLATE,
    TASK_DOCKERFILE_TEMPLATE,
    TASKS_CSV_HEADER,
)


def generate_base_dockerfile(dataset: Dataset) -> str:
    """Generate the base Dockerfile for a dataset."""
    return BASE_DOCKERFILE_TEMPLATE.format(base_image=dataset.base_image)


def generate_requirements_txt() -> str:
    """Generate requirements.txt content."""
    return REQUIREMENTS_TXT


def generate_task_dockerfile(dataset_id: str, dockerhub_username: str = "afterquery") -> str:
    """Generate the task-specific Dockerfile that extends the base image."""
    return TASK_DOCKERFILE_TEMPLATE.format(
        dockerhub_username=dockerhub_username,
        dataset_id=dataset_id,
    )


def generate_instance_info(task: Task) -> str:
    """Generate instance_info.txt content for a task."""
    return INSTANCE_INFO_TEMPLATE.format(
        instance_id=task.instance_id,
        task_id=task.task_id,
        fail_to_pass=task.test_spec.to_fail_to_pass_str(),
        pass_to_pass=task.test_spec.to_pass_to_pass_str(),
    )


def generate_run_script(task: Task) -> str:
    """Generate run_script.sh content with embedded tests."""
    return RUN_SCRIPT_TEMPLATE.format(
        task_id=task.task_id,
        test_code=task.test_code,
    )


def get_parser_py() -> str:
    """Get the static parser.py content."""
    return PARSER_PY


def generate_tasks_csv_row(task: Task) -> str:
    """Generate a single CSV row for a task.

    Uses proper CSV escaping for fields that may contain commas, newlines, or quotes.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Format fail_to_pass and pass_to_pass as JSON-like string lists
    fail_to_pass_str = str(task.test_spec.fail_to_pass)
    pass_to_pass_str = str(task.test_spec.pass_to_pass)

    row = [
        task.repo,
        task.instance_id,
        task.base_commit,
        task.patch,
        "",  # test_patch (usually empty)
        task.problem_statement,
        task.requirements,
        task.interface,
        task.language,
        fail_to_pass_str,
        pass_to_pass_str,
        task.issue_specificity,
        task.issue_categories,
        task.before_repo_set_cmd,
        f"tasks/{task.task_id}/task_tests.py",  # selected_test_files_to_run
    ]

    writer.writerow(row)
    return output.getvalue().strip()


def generate_tasks_csv(task: Task) -> str:
    """Generate complete tasks.csv file content (header + row)."""
    header = TASKS_CSV_HEADER
    row = generate_tasks_csv_row(task)
    return f"{header}\n{row}\n"


def write_task_files(
    dataset_path: Path,
    task: Task,
    dockerhub_username: str = "afterquery",
) -> list[Path]:
    """Write all files for a task to the dataset directory.

    Returns list of created file paths.
    """
    task_dir = dataset_path / task.task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    created_files = []

    # Write Dockerfile
    dockerfile_path = task_dir / "Dockerfile"
    dockerfile_content = generate_task_dockerfile(
        dataset_id=dataset_path.name,
        dockerhub_username=dockerhub_username,
    )
    dockerfile_path.write_text(dockerfile_content)
    created_files.append(dockerfile_path)

    # Write instance_info.txt
    instance_info_path = task_dir / "instance_info.txt"
    instance_info_path.write_text(generate_instance_info(task))
    created_files.append(instance_info_path)

    # Write run_script.sh
    run_script_path = task_dir / "run_script.sh"
    run_script_path.write_text(generate_run_script(task))
    run_script_path.chmod(0o755)  # Make executable
    created_files.append(run_script_path)

    # Write task_tests.py
    tests_path = task_dir / "task_tests.py"
    tests_path.write_text(task.test_code)
    created_files.append(tests_path)

    # Write parser.py
    parser_path = task_dir / "parser.py"
    parser_path.write_text(get_parser_py())
    created_files.append(parser_path)

    # Write tasks.csv
    csv_path = task_dir / "tasks.csv"
    csv_path.write_text(generate_tasks_csv(task))
    created_files.append(csv_path)

    return created_files


def write_dataset_base_files(dataset: Dataset, dataset_path: Path) -> list[Path]:
    """Write base files for a dataset (Dockerfile, requirements.txt).

    Returns list of created file paths.
    """
    dataset_path.mkdir(parents=True, exist_ok=True)

    created_files = []

    # Write Dockerfile
    dockerfile_path = dataset_path / "Dockerfile"
    dockerfile_path.write_text(generate_base_dockerfile(dataset))
    created_files.append(dockerfile_path)

    # Write requirements.txt
    requirements_path = dataset_path / "requirements.txt"
    requirements_path.write_text(generate_requirements_txt())
    created_files.append(requirements_path)

    return created_files
