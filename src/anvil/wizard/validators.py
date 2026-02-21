"""Validation functions for task creation."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path


def validate_dataset_id(dataset_id: str) -> list[str]:
    """Validate dataset identifier format.

    Rules:
    - Alphanumeric and hyphens only
    - Must start with a letter
    - Cannot end with hyphen
    """
    errors = []
    if not dataset_id:
        errors.append("Dataset ID cannot be empty")
        return errors

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]$|^[a-zA-Z]$", dataset_id):
        errors.append(
            f"Dataset ID must start with a letter, contain only alphanumeric "
            f"characters and hyphens, and not end with a hyphen: {dataset_id}"
        )

    return errors


def validate_task_id(task_id: str, existing_ids: set[str] | None = None) -> list[str]:
    """Validate task ID format and uniqueness.

    Rules:
    - Must match pattern 'task-N' where N is a positive integer
    - Must be unique within the dataset
    """
    errors = []

    if not re.match(r"^task-\d+$", task_id):
        errors.append(f"Task ID must match pattern 'task-N' (e.g., task-1): {task_id}")

    if existing_ids and task_id in existing_ids:
        errors.append(f"Task ID already exists: {task_id}")

    return errors


def validate_python_syntax(code: str) -> list[str]:
    """Validate Python code syntax."""
    errors = []

    if not code.strip():
        errors.append("Python code is empty")
        return errors

    try:
        ast.parse(code)
    except SyntaxError as e:
        errors.append(f"Python syntax error at line {e.lineno}: {e.msg}")

    return errors


def validate_patch_format(patch: str) -> list[str]:
    """Validate git diff patch format."""
    errors = []

    if not patch.strip():
        errors.append("Patch is empty")
        return errors

    lines = patch.split("\n")
    has_diff_header = any(line.startswith("diff --git") for line in lines)
    has_file_markers = any(line.startswith("---") or line.startswith("+++") for line in lines)
    has_hunk_header = any(line.startswith("@@") for line in lines)

    if not (has_diff_header or has_file_markers):
        errors.append(
            "Patch does not appear to be valid git diff format. "
            "Expected 'diff --git' header or '---/+++' file markers."
        )

    if not has_hunk_header:
        errors.append("Patch is missing hunk headers (@@...@@)")

    return errors


def extract_test_names(test_code: str) -> list[str]:
    """Extract test function names from Python test code."""
    # Match function definitions starting with 'test_'
    pattern = re.compile(r"def (test_\w+)\s*\(")
    return pattern.findall(test_code)


def validate_test_names(
    test_code: str,
    fail_to_pass: list[str],
    pass_to_pass: list[str],
) -> list[str]:
    """Validate that specified tests exist in test code."""
    errors = []

    defined_tests = set(extract_test_names(test_code))

    if not defined_tests:
        errors.append("No test functions found in test code (expected functions named 'test_*')")
        return errors

    for test in fail_to_pass:
        if test not in defined_tests:
            errors.append(f"FAIL_TO_PASS test '{test}' not found in test code")

    for test in pass_to_pass:
        if test not in defined_tests:
            errors.append(f"PASS_TO_PASS test '{test}' not found in test code")

    return errors


def validate_base_commit(commit: str) -> list[str]:
    """Validate base commit SHA format."""
    errors = []

    if not commit:
        errors.append("Base commit cannot be empty")
        return errors

    # Git commit SHA is 40 hex characters (full) or 7+ (abbreviated)
    if not re.match(r"^[a-fA-F0-9]{7,40}$", commit):
        errors.append(
            f"Base commit must be a valid git SHA (7-40 hex characters): {commit}"
        )

    return errors


def validate_repo_has_git(repo_path: Path) -> list[str]:
    """Validate that a repository directory contains a .git directory."""
    errors = []
    if not (repo_path / ".git").exists():
        errors.append(
            f"Repository at {repo_path} is missing a .git directory. "
            f"The repository must be a valid git repo with commit history "
            f"so that base_commit alignment and patch application work correctly."
        )
    return errors


def validate_commit_exists_in_repo(repo_path: Path, commit: str) -> list[str]:
    """Validate that a commit SHA exists in the repository's git history."""
    errors = []
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"{commit}^{{commit}}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            errors.append(
                f"Commit {commit} does not exist in the repository at {repo_path}. "
                f"Ensure the base_commit matches a real commit in the repo's git history."
            )
    except FileNotFoundError:
        errors.append("git is not installed or not on PATH")
    return errors


def validate_patch_applies(repo_path: Path, patch: str, base_commit: str) -> list[str]:
    """Validate that a patch applies cleanly against the base_commit."""
    errors = []
    try:
        # First checkout the base commit in a detached HEAD
        subprocess.run(
            ["git", "stash", "--include-untracked"],
            cwd=repo_path,
            capture_output=True,
        )
        checkout = subprocess.run(
            ["git", "checkout", base_commit],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if checkout.returncode != 0:
            errors.append(f"Could not checkout base_commit {base_commit}: {checkout.stderr.strip()}")
            # Restore original state
            subprocess.run(["git", "checkout", "-"], cwd=repo_path, capture_output=True)
            subprocess.run(["git", "stash", "pop"], cwd=repo_path, capture_output=True)
            return errors

        # Dry-run the patch
        result = subprocess.run(
            ["git", "apply", "--check", "--ignore-whitespace"],
            input=patch,
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            errors.append(
                f"Patch does not apply cleanly against base_commit {base_commit[:12]}:\n"
                f"  {result.stderr.strip()}\n"
                f"  Ensure the patch context lines match the actual file contents at that commit."
            )

        # Restore original state
        subprocess.run(["git", "checkout", "-"], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "stash", "pop"], cwd=repo_path, capture_output=True)
    except FileNotFoundError:
        errors.append("git is not installed or not on PATH")
    return errors


def validate_dataset_structure(dataset_path: Path) -> list[str]:
    """Validate complete dataset directory structure."""
    errors = []

    if not dataset_path.exists():
        errors.append(f"Dataset directory does not exist: {dataset_path}")
        return errors

    if not dataset_path.is_dir():
        errors.append(f"Dataset path is not a directory: {dataset_path}")
        return errors

    # Check for base Dockerfile
    dockerfile = dataset_path / "Dockerfile"
    if not dockerfile.exists():
        errors.append(f"Missing base Dockerfile: {dockerfile}")

    # Check for requirements.txt
    requirements = dataset_path / "requirements.txt"
    if not requirements.exists():
        errors.append(f"Missing requirements.txt: {requirements}")

    return errors


def validate_task_structure(task_path: Path) -> list[str]:
    """Validate task directory structure."""
    errors = []

    if not task_path.exists():
        errors.append(f"Task directory does not exist: {task_path}")
        return errors

    required_files = [
        "Dockerfile",
        "instance_info.txt",
        "run_script.sh",
        "task_tests.py",
        "parser.py",
        "tasks.csv",
    ]

    for filename in required_files:
        filepath = task_path / filename
        if not filepath.exists():
            errors.append(f"Missing required file: {filepath}")

    return errors


def validate_all_tasks(dataset_path: Path) -> dict[str, list[str]]:
    """Validate all tasks in a dataset.

    Returns a dict mapping task_id to list of errors.
    """
    results = {}

    # Find all task directories
    for item in dataset_path.iterdir():
        if item.is_dir() and item.name.startswith("task-"):
            errors = validate_task_structure(item)
            if errors:
                results[item.name] = errors

    return results
