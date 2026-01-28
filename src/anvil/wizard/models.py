"""Data models for task creation wizard."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TestSpec:
    """Specification for test expectations."""

    fail_to_pass: list[str] = field(default_factory=list)
    pass_to_pass: list[str] = field(default_factory=list)

    def to_fail_to_pass_str(self) -> str:
        """Format fail_to_pass as a string list for instance_info.txt."""
        return "[" + ", ".join(f"'{t}'" for t in self.fail_to_pass) + "]"

    def to_pass_to_pass_str(self) -> str:
        """Format pass_to_pass as a string list for instance_info.txt."""
        return "[" + ", ".join(f"'{t}'" for t in self.pass_to_pass) + "]"


@dataclass
class Task:
    """A single evaluation task."""

    task_id: str
    instance_id: str
    problem_statement: str
    patch: str
    test_code: str
    test_spec: TestSpec
    base_commit: str
    repo: str
    language: str = "Python"
    before_repo_set_cmd: str = ""
    requirements: str = ""
    interface: str = ""
    issue_specificity: str = ""
    issue_categories: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Create a Task from a dictionary."""
        test_spec = TestSpec(
            fail_to_pass=data.get("fail_to_pass", []),
            pass_to_pass=data.get("pass_to_pass", []),
        )
        return cls(
            task_id=data["task_id"],
            instance_id=data["instance_id"],
            problem_statement=data["problem_statement"],
            patch=data["patch"],
            test_code=data["test_code"],
            test_spec=test_spec,
            base_commit=data["base_commit"],
            repo=data["repo"],
            language=data.get("language", "Python"),
            before_repo_set_cmd=data.get("before_repo_set_cmd", ""),
            requirements=data.get("requirements", ""),
            interface=data.get("interface", ""),
            issue_specificity=data.get("issue_specificity", ""),
            issue_categories=data.get("issue_categories", ""),
        )

    def to_dict(self) -> dict:
        """Convert Task to a dictionary."""
        return {
            "task_id": self.task_id,
            "instance_id": self.instance_id,
            "problem_statement": self.problem_statement,
            "patch": self.patch,
            "test_code": self.test_code,
            "fail_to_pass": self.test_spec.fail_to_pass,
            "pass_to_pass": self.test_spec.pass_to_pass,
            "base_commit": self.base_commit,
            "repo": self.repo,
            "language": self.language,
            "before_repo_set_cmd": self.before_repo_set_cmd,
            "requirements": self.requirements,
            "interface": self.interface,
            "issue_specificity": self.issue_specificity,
            "issue_categories": self.issue_categories,
        }


@dataclass
class Dataset:
    """A dataset containing multiple evaluation tasks."""

    dataset_id: str
    repo_path: Path | None = None
    repo_url: str | None = None
    base_image: str = "ubuntu:24.04"
    language: str = "python"
    tasks: list[Task] = field(default_factory=list)

    @property
    def repo_name(self) -> str:
        """Get the repository name from path or URL."""
        if self.repo_path:
            return self.repo_path.name
        if self.repo_url:
            # Extract repo name from URL like https://github.com/user/repo.git
            name = self.repo_url.rstrip("/").split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            return name
        return self.dataset_id

    def get_next_task_id(self) -> str:
        """Get the next available task ID."""
        existing_nums = []
        for task in self.tasks:
            if task.task_id.startswith("task-"):
                try:
                    num = int(task.task_id.split("-")[1])
                    existing_nums.append(num)
                except (IndexError, ValueError):
                    pass
        next_num = max(existing_nums, default=0) + 1
        return f"task-{next_num}"

    def add_task(self, task: Task) -> None:
        """Add a task to the dataset."""
        self.tasks.append(task)

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
