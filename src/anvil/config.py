"""Path configuration for anvil."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return the anvil repository root directory."""
    return Path(__file__).resolve().parents[2]


def datasets_dir() -> Path:
    """Return the datasets directory."""
    return repo_root() / "datasets"


def dataset_dir(dataset_id: str) -> Path:
    """Return the directory for a specific dataset."""
    return datasets_dir() / dataset_id


def tasks_dir(dataset_id: str) -> Path:
    """Return the tasks directory for a dataset."""
    return dataset_dir(dataset_id) / "tasks"


def runs_dir(dataset_id: str) -> Path:
    """Return the runs directory for a dataset."""
    return dataset_dir(dataset_id) / "runs"


def eval_dir(dataset_id: str, eval_id: str) -> Path:
    """Return the output directory for an evaluation run."""
    return runs_dir(dataset_id) / eval_id


# Alias for backwards compatibility
eval_output_dir = eval_dir


def swe_bench_eval_script() -> Path:
    """Return the path to the SWE-bench Pro evaluation script."""
    return Path(__file__).parent / "_vendor" / "swe_bench_pro" / "swe_bench_pro_eval.py"


def swe_agent_dir() -> Path:
    """Path to SWE-agent submodule (if present)."""
    return repo_root() / "SWE-agent"


def defaults_dir() -> Path:
    """Path to agent defaults directory."""
    return Path(__file__).parent / "agents" / "defaults"


def default_sweagent_config_template() -> Path:
    return defaults_dir() / "sweagent_config.yaml"


def default_minisweagent_config_template() -> Path:
    return defaults_dir() / "minisweagent_config.yaml"
