"""CLI commands for task creation wizard."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from .generators import write_dataset_base_files, write_task_files
from .models import Dataset, Task, TestSpec
from .validators import (
    extract_test_names,
    validate_all_tasks,
    validate_base_commit,
    validate_commit_exists_in_repo,
    validate_dataset_id,
    validate_dataset_structure,
    validate_patch_applies,
    validate_patch_format,
    validate_python_syntax,
    validate_repo_has_git,
    validate_task_id,
    validate_test_names,
)


def _get_repo_head_commit(repo_path: Path) -> str | None:
    """Get the HEAD commit SHA from a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _get_git_diff(repo_path: Path) -> str:
    """Get the current git diff (staged + unstaged changes)."""
    try:
        # Get both staged and unstaged changes
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _has_uncommitted_changes(repo_path: Path) -> bool:
    """Check if repo has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _reset_repo(repo_path: Path) -> bool:
    """Reset repo to clean state (discard all uncommitted changes)."""
    try:
        # Discard all changes
        subprocess.run(
            ["git", "checkout", "."],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        # Clean untracked files
        subprocess.run(
            ["git", "clean", "-fd"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _find_repo_in_dataset(dataset_path: Path) -> Path | None:
    """Find the git repository directory in a dataset."""
    for item in dataset_path.iterdir():
        if item.is_dir() and (item / ".git").exists():
            return item
    return None


def _find_repo_dir_in_dataset(dataset_path: Path) -> Path | None:
    """Find the repository directory in a dataset, whether or not it has .git.

    Looks for any directory that isn't a task directory (task-*).
    Falls back to _find_repo_in_dataset if nothing else is found.
    """
    for item in sorted(dataset_path.iterdir()):
        if item.is_dir() and not item.name.startswith("task-"):
            return item
    return None


def _get_existing_task_ids(dataset_path: Path) -> set[str]:
    """Get all existing task IDs in a dataset."""
    task_ids = set()
    if dataset_path.exists():
        for item in dataset_path.iterdir():
            if item.is_dir() and item.name.startswith("task-"):
                task_ids.add(item.name)
    return task_ids


def _get_next_task_id(dataset_path: Path) -> str:
    """Get the next available task ID."""
    existing = _get_existing_task_ids(dataset_path)
    max_num = 0
    for task_id in existing:
        try:
            num = int(task_id.split("-")[1])
            max_num = max(max_num, num)
        except (IndexError, ValueError):
            pass
    return f"task-{max_num + 1}"


def _read_file_or_value(file_path: Path | None, value: str | None) -> str | None:
    """Read content from file or return direct value."""
    if file_path and file_path.exists():
        return file_path.read_text()
    return value


def _parse_comma_separated(value: str | None) -> list[str]:
    """Parse comma-separated string into list."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def init_dataset(
    dataset_id: Annotated[str, typer.Option("--dataset", "-d", help="Dataset identifier")],
    repo_path: Annotated[
        Path | None, typer.Option("--repo-path", help="Local path to repository")
    ] = None,
    repo_url: Annotated[
        str | None, typer.Option("--repo-url", help="Git URL to clone")
    ] = None,
    base_image: Annotated[
        str, typer.Option("--base-image", help="Base Docker image")
    ] = "ubuntu:24.04",
    language: Annotated[
        str, typer.Option("--language", "-l", help="Primary language")
    ] = "python",
    output_dir: Annotated[
        Path | None, typer.Option("--output-dir", "-o", help="Output directory")
    ] = None,
    interactive: Annotated[
        bool, typer.Option("--interactive", "-i", help="Run interactive wizard")
    ] = False,
) -> None:
    """Initialize a new evaluation dataset.

    Creates the base directory structure with Dockerfile and requirements.txt.
    Optionally clones or links a repository.
    """
    # Interactive mode
    if interactive:
        if not dataset_id:
            dataset_id = typer.prompt("Dataset identifier")
        if not repo_path and not repo_url:
            repo_input = typer.prompt("Repository path or URL")
            if repo_input.startswith(("http://", "https://", "git@")):
                repo_url = repo_input
            else:
                repo_path = Path(repo_input)
        base_image = typer.prompt("Base Docker image", default=base_image)
        language = typer.prompt("Primary language", default=language)

    # Validation
    errors = validate_dataset_id(dataset_id)
    if errors:
        for err in errors:
            typer.secho(f"Error: {err}", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not repo_path and not repo_url:
        typer.secho(
            "Error: Either --repo-path or --repo-url must be provided",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # Determine output directory
    if output_dir:
        dataset_path = output_dir / dataset_id
    else:
        dataset_path = Path.cwd() / dataset_id

    if dataset_path.exists():
        if not typer.confirm(f"Directory {dataset_path} already exists. Overwrite?"):
            raise typer.Exit(0)

    # Create dataset object
    dataset = Dataset(
        dataset_id=dataset_id,
        repo_path=repo_path,
        repo_url=repo_url,
        base_image=base_image,
        language=language,
    )

    # Create directory and base files
    typer.echo(f"Creating dataset at {dataset_path}...")
    created_files = write_dataset_base_files(dataset, dataset_path)

    # Handle repository
    repo_dest = dataset_path / dataset.repo_name
    if repo_url:
        typer.echo(f"Cloning repository from {repo_url}...")
        try:
            subprocess.run(
                ["git", "clone", repo_url, str(repo_dest)],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            typer.secho(f"Error cloning repository: {e}", fg=typer.colors.RED)
            raise typer.Exit(1)
    elif repo_path:
        if repo_path.is_absolute():
            source = repo_path
        else:
            source = Path.cwd() / repo_path

        if not source.exists():
            typer.secho(f"Error: Repository path does not exist: {source}", fg=typer.colors.RED)
            raise typer.Exit(1)

        typer.echo(f"Copying repository from {source}...")
        shutil.copytree(source, repo_dest, dirs_exist_ok=True)

    # Validate .git exists in the repo
    if repo_dest.exists():
        errors = validate_repo_has_git(repo_dest)
        if errors:
            for err in errors:
                typer.secho(f"Error: {err}", fg=typer.colors.RED)
            raise typer.Exit(1)

    # Summary
    typer.secho("\nDataset initialized successfully!", fg=typer.colors.GREEN)
    typer.echo("\nCreated files:")
    for f in created_files:
        typer.echo(f"  - {f.relative_to(dataset_path)}")
    if repo_dest.exists():
        typer.echo(f"  - {repo_dest.relative_to(dataset_path)}/")

    typer.secho("\n" + "=" * 60, fg=typer.colors.CYAN)
    typer.secho("NEXT STEPS", fg=typer.colors.CYAN, bold=True)
    typer.secho("=" * 60, fg=typer.colors.CYAN)

    typer.echo("\n1. Create a task with problem statement, tests, and solution:")
    typer.echo(f"   anvil add-task -d {dataset_path} \\")
    typer.echo("     --problem-file problem.md \\")
    typer.echo("     --tests-file tests.py \\")
    typer.echo("     --capture-diff")
    typer.echo("")
    typer.echo("   Or provide a pre-made patch:")
    typer.echo(f"   anvil add-task -d {dataset_path} \\")
    typer.echo("     --problem-file problem.md \\")
    typer.echo("     --tests-file tests.py \\")
    typer.echo("     --patch-file solution.diff")

    typer.echo("\n2. Convert to Anvil evaluation format:")
    typer.echo(f"   anvil convert-dataset -d {dataset_path} -u <dockerhub-username>")

    typer.echo("\n3. Publish images and verify with oracle:")
    typer.echo(f"   anvil publish-images -d {dataset_path} -u <username> --repo <repo>")
    typer.echo(f"   anvil run-evals -d {dataset_path} --agent oracle -u <username> --dockerhub-repo <repo>")

    typer.secho("\nFor detailed guidance, see: docs/TASK_CREATION_GUIDE.md", fg=typer.colors.YELLOW)


def add_task(
    dataset: Annotated[str, typer.Option("--dataset", "-d", help="Dataset path or ID")],
    task_id: Annotated[
        str | None, typer.Option("--task-id", help="Task ID (auto-generated if omitted)")
    ] = None,
    problem_statement: Annotated[
        str | None, typer.Option("--problem-statement", "-p", help="Problem statement text")
    ] = None,
    problem_file: Annotated[
        Path | None, typer.Option("--problem-file", help="Path to problem statement file")
    ] = None,
    patch: Annotated[
        str | None, typer.Option("--patch", help="Git diff patch content")
    ] = None,
    patch_file: Annotated[
        Path | None, typer.Option("--patch-file", help="Path to patch file")
    ] = None,
    tests: Annotated[
        str | None, typer.Option("--tests", help="Pytest test code")
    ] = None,
    tests_file: Annotated[
        Path | None, typer.Option("--tests-file", help="Path to test file")
    ] = None,
    fail_to_pass: Annotated[
        str | None, typer.Option("--fail-to-pass", help="Tests that FAIL before patch, PASS after (comma-separated)")
    ] = None,
    pass_to_pass: Annotated[
        str | None, typer.Option("--pass-to-pass", help="Tests that PASS both before and after patch (comma-separated)")
    ] = None,
    base_commit: Annotated[
        str | None, typer.Option("--base-commit", help="Base commit SHA")
    ] = None,
    repo_name: Annotated[
        str | None, typer.Option("--repo-name", help="Repository name for instance_id")
    ] = None,
    dockerhub_username: Annotated[
        str, typer.Option("--dockerhub-username", "-u", help="Docker Hub username")
    ] = "afterquery",
    interactive: Annotated[
        bool, typer.Option("--interactive", "-i", help="Run interactive wizard")
    ] = False,
    capture_diff: Annotated[
        bool, typer.Option("--capture-diff", "-c", help="Capture diff from repo changes, then reset")
    ] = False,
) -> None:
    """Add a new task to an existing dataset.

    Creates all required files in a new task directory.

    Use --capture-diff to interactively make changes to the repo:
    1. Records current commit as base
    2. Prompts you to make changes
    3. Captures git diff as the solution
    4. Resets repo to clean state for next task
    """
    # Resolve dataset path
    dataset_path = Path(dataset)
    if not dataset_path.is_absolute():
        dataset_path = Path.cwd() / dataset

    if not dataset_path.exists():
        typer.secho(f"Error: Dataset directory does not exist: {dataset_path}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Get existing task IDs
    existing_ids = _get_existing_task_ids(dataset_path)

    # Auto-generate task ID if not provided
    if not task_id:
        task_id = _get_next_task_id(dataset_path)
        if interactive or capture_diff:
            task_id = typer.prompt("Task ID", default=task_id)

    # Handle --capture-diff mode
    if capture_diff:
        repo_path = _find_repo_in_dataset(dataset_path)
        if not repo_path:
            typer.secho("Error: No git repository found in dataset", fg=typer.colors.RED)
            raise typer.Exit(1)

        # Record base commit
        base_commit = _get_repo_head_commit(repo_path)
        if not base_commit:
            typer.secho("Error: Could not get HEAD commit from repo", fg=typer.colors.RED)
            raise typer.Exit(1)

        typer.secho(f"\n" + "=" * 60, fg=typer.colors.CYAN)
        typer.secho("CAPTURE DIFF MODE", fg=typer.colors.CYAN, bold=True)
        typer.secho("=" * 60, fg=typer.colors.CYAN)
        typer.echo(f"\nRepository: {repo_path}")
        typer.echo(f"Base commit: {base_commit[:12]}")
        typer.echo("")
        typer.secho("How this works:", fg=typer.colors.YELLOW)
        typer.echo("  1. Make changes to the repo that solve the task")
        typer.echo("  2. Type 'done' when finished - the diff will be captured")
        typer.echo("  3. The repo will be reset for the next task")

        # Check if there are already changes
        if _has_uncommitted_changes(repo_path):
            typer.echo(f"\nCurrent diff:")
            current_diff = _get_git_diff(repo_path)
            typer.echo(current_diff[:500] + "..." if len(current_diff) > 500 else current_diff)

            if not typer.confirm("\nUse these existing changes?", default=True):
                if typer.confirm("Reset repo and start fresh?", default=False):
                    _reset_repo(repo_path)
                    typer.secho("Repo reset to clean state.", fg=typer.colors.GREEN)
                else:
                    raise typer.Exit(0)

        # If no changes yet, prompt user to make them
        if not _has_uncommitted_changes(repo_path):
            typer.secho(f"\nMake your changes to the repository now.", fg=typer.colors.YELLOW)
            typer.echo(f"Edit files in: {repo_path}")
            typer.echo("")
            while True:
                response = typer.prompt("Type 'done' when finished making changes")
                if response.lower().strip() == "done":
                    break
                typer.echo("Please type 'done' to continue.")

            if not _has_uncommitted_changes(repo_path):
                typer.secho("Error: No changes detected in repository", fg=typer.colors.RED)
                raise typer.Exit(1)

        # Capture the diff
        patch = _get_git_diff(repo_path)
        if not patch.strip():
            typer.secho("Error: Empty diff captured", fg=typer.colors.RED)
            raise typer.Exit(1)

        typer.secho(f"\nCaptured diff ({len(patch)} bytes)", fg=typer.colors.GREEN)

        # Show diff preview
        lines = patch.split('\n')
        if len(lines) > 20:
            typer.echo('\n'.join(lines[:20]))
            typer.echo(f"... ({len(lines) - 20} more lines)")
        else:
            typer.echo(patch)

        if not typer.confirm("\nUse this diff?", default=True):
            raise typer.Exit(0)

        # Reset repo for next task
        if typer.confirm("\nReset repo to clean state for next task?", default=True):
            if _reset_repo(repo_path):
                typer.secho("Repo reset successfully.", fg=typer.colors.GREEN)
            else:
                typer.secho("Warning: Failed to reset repo", fg=typer.colors.YELLOW)

    # Interactive mode for missing fields
    if interactive:
        if not problem_statement and not problem_file:
            typer.echo("Enter problem statement (Ctrl+D when done):")
            lines = []
            try:
                while True:
                    lines.append(input())
            except EOFError:
                pass
            problem_statement = "\n".join(lines)

        if not patch and not patch_file:
            typer.echo("Enter patch/solution (Ctrl+D when done):")
            lines = []
            try:
                while True:
                    lines.append(input())
            except EOFError:
                pass
            patch = "\n".join(lines)

        if not tests and not tests_file:
            typer.echo("Enter test code (Ctrl+D when done):")
            lines = []
            try:
                while True:
                    lines.append(input())
            except EOFError:
                pass
            tests = "\n".join(lines)

    # Read content from files or direct values
    problem_content = _read_file_or_value(problem_file, problem_statement)
    patch_content = _read_file_or_value(patch_file, patch)
    tests_content = _read_file_or_value(tests_file, tests)

    # Validate required fields
    if not problem_content:
        typer.secho("Error: Problem statement is required", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not patch_content:
        typer.secho("Error: Patch is required", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not tests_content:
        typer.secho("Error: Tests are required", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Validate task ID
    errors = validate_task_id(task_id, existing_ids)
    if errors:
        for err in errors:
            typer.secho(f"Error: {err}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Validate Python syntax
    errors = validate_python_syntax(tests_content)
    if errors:
        for err in errors:
            typer.secho(f"Error: {err}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Validate patch format
    errors = validate_patch_format(patch_content)
    if errors:
        for err in errors:
            typer.secho(f"Warning: {err}", fg=typer.colors.YELLOW)

    # Parse test names
    fail_to_pass_list = _parse_comma_separated(fail_to_pass)
    pass_to_pass_list = _parse_comma_separated(pass_to_pass)

    # Auto-detect test names if not provided
    if not fail_to_pass_list:
        detected_tests = extract_test_names(tests_content)
        if interactive and detected_tests:
            typer.echo("")
            typer.secho("Test Classification:", fg=typer.colors.YELLOW)
            typer.echo("  FAIL_TO_PASS: Tests that FAIL before the patch and PASS after.")
            typer.echo("                These verify the new functionality being added.")
            typer.echo("  PASS_TO_PASS: Tests that PASS both before and after (regression tests).")
            typer.echo("")
            typer.echo(f"Detected tests: {', '.join(detected_tests)}")
            fail_to_pass_input = typer.prompt(
                "FAIL_TO_PASS tests (comma-separated)",
                default=",".join(detected_tests),
            )
            fail_to_pass_list = _parse_comma_separated(fail_to_pass_input)
        elif detected_tests:
            fail_to_pass_list = detected_tests
            typer.echo(f"\nAuto-detected FAIL_TO_PASS tests: {', '.join(fail_to_pass_list)}")
            typer.secho("  (These tests should FAIL before your patch and PASS after)", fg=typer.colors.YELLOW)

    # Validate test names
    errors = validate_test_names(tests_content, fail_to_pass_list, pass_to_pass_list)
    if errors:
        for err in errors:
            typer.secho(f"Error: {err}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Auto-detect base commit
    if not base_commit:
        # Try to find a git repo in the dataset
        for item in dataset_path.iterdir():
            if item.is_dir() and (item / ".git").exists():
                base_commit = _get_repo_head_commit(item)
                if base_commit:
                    typer.echo(f"Auto-detected base commit: {base_commit[:12]}")
                    break

    if not base_commit:
        if interactive:
            base_commit = typer.prompt("Base commit SHA")
        else:
            typer.secho("Error: Base commit is required (--base-commit)", fg=typer.colors.RED)
            raise typer.Exit(1)

    # Validate base commit
    errors = validate_base_commit(base_commit)
    if errors:
        for err in errors:
            typer.secho(f"Error: {err}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Validate .git exists and commit is reachable
    repo_dir = _find_repo_dir_in_dataset(dataset_path)
    if repo_dir:
        errors = validate_repo_has_git(repo_dir)
        if errors:
            for err in errors:
                typer.secho(f"Error: {err}", fg=typer.colors.RED)
            raise typer.Exit(1)

        errors = validate_commit_exists_in_repo(repo_dir, base_commit)
        if errors:
            for err in errors:
                typer.secho(f"Error: {err}", fg=typer.colors.RED)
            raise typer.Exit(1)

        # Dry-run patch to verify it applies cleanly
        errors = validate_patch_applies(repo_dir, patch_content, base_commit)
        if errors:
            for err in errors:
                typer.secho(f"Error: {err}", fg=typer.colors.RED)
            raise typer.Exit(1)
        typer.echo("Patch applies cleanly against base commit.")

    # Determine repo name
    if not repo_name:
        # Try to find repo directory
        for item in dataset_path.iterdir():
            if item.is_dir() and (item / ".git").exists():
                repo_name = item.name
                break
        if not repo_name:
            repo_name = dataset_path.name

    # Create task object
    # instance_id prefix must match repo_name because publish.py uses
    # partition(".")[0] to look up the docker_image_creation context directory,
    # and AfterQueryFront names that directory after repoName.
    instance_id = f"{repo_name}.{task_id}"
    task = Task(
        task_id=task_id,
        instance_id=instance_id,
        problem_statement=problem_content,
        patch=patch_content,
        test_code=tests_content,
        test_spec=TestSpec(
            fail_to_pass=fail_to_pass_list,
            pass_to_pass=pass_to_pass_list,
        ),
        base_commit=base_commit,
        repo=f"{dockerhub_username}/{repo_name}",
    )

    # Confirm in interactive mode
    if interactive:
        typer.echo(f"\nTask summary:")
        typer.echo(f"  Task ID: {task_id}")
        typer.echo(f"  Instance ID: {instance_id}")
        typer.echo(f"  Base commit: {base_commit[:12]}")
        typer.echo(f"  FAIL_TO_PASS: {len(fail_to_pass_list)} tests")
        typer.echo(f"  PASS_TO_PASS: {len(pass_to_pass_list)} tests")
        if not typer.confirm("\nCreate task?", default=True):
            raise typer.Exit(0)

    # Write task files
    typer.echo(f"\nCreating task {task_id}...")
    created_files = write_task_files(dataset_path, task, dockerhub_username)

    # Summary
    typer.secho(f"\nTask {task_id} created successfully!", fg=typer.colors.GREEN)
    typer.echo("\nCreated files:")
    for f in created_files:
        typer.echo(f"  - {f.relative_to(dataset_path)}")

    # Show next steps
    existing_count = len(_get_existing_task_ids(dataset_path))
    typer.secho(f"\nDataset now has {existing_count} task(s).", fg=typer.colors.CYAN)
    typer.echo("\nNext steps:")
    typer.echo(f"  - Add another task:  anvil add-task -d {dataset_path} --capture-diff ...")
    typer.echo(f"  - Validate dataset:  anvil validate-dataset -d {dataset_path}")
    typer.echo(f"  - Convert & publish: anvil convert-dataset -d {dataset_path} -u <username>")


def validate_dataset(
    dataset: Annotated[str, typer.Option("--dataset", "-d", help="Dataset path or ID")],
    fix: Annotated[
        bool, typer.Option("--fix", help="Attempt to fix issues")
    ] = False,
) -> None:
    """Validate dataset structure and task definitions."""
    # Resolve dataset path
    dataset_path = Path(dataset)
    if not dataset_path.is_absolute():
        dataset_path = Path.cwd() / dataset

    typer.echo(f"Validating dataset at {dataset_path}...")

    # Validate base structure
    base_errors = validate_dataset_structure(dataset_path)

    # Validate all tasks
    task_errors = validate_all_tasks(dataset_path)

    # Report results
    has_errors = bool(base_errors or task_errors)

    if base_errors:
        typer.secho("\nDataset structure errors:", fg=typer.colors.RED)
        for err in base_errors:
            typer.echo(f"  - {err}")

    if task_errors:
        typer.secho("\nTask errors:", fg=typer.colors.RED)
        for task_id, errors in task_errors.items():
            typer.echo(f"\n  {task_id}:")
            for err in errors:
                typer.echo(f"    - {err}")

    if not has_errors:
        task_count = len(_get_existing_task_ids(dataset_path))
        typer.secho(
            f"\nDataset is valid! ({task_count} task(s) found)",
            fg=typer.colors.GREEN,
        )
        typer.echo("\nNext steps:")
        typer.echo(f"  1. Convert:  anvil convert-dataset -d {dataset_path} -u <dockerhub-username>")
        typer.echo(f"  2. Publish:  anvil publish-images -d {dataset_path} -u <username> --repo <repo>")
        typer.echo(f"  3. Verify:   anvil run-evals -d {dataset_path} --agent oracle -u <username> --dockerhub-repo <repo>")
    else:
        typer.secho("\nValidation failed with errors above.", fg=typer.colors.RED)
        typer.echo("\nFix the errors and run validation again.")
        raise typer.Exit(1)
