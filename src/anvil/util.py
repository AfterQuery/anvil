import itertools
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, TypeVar

import typer

T = TypeVar("T")


def run(
    cmd: list[str] | str,
    cwd: Path | None = None,
    env: dict | None = None,
    quiet: bool = False,
) -> int:
    """Run a shell command and return its exit code."""
    if not quiet:
        typer.echo(f"Running: {cmd}")

    return subprocess.run(
        cmd,
        cwd=cwd,
        env={**os.environ, **env} if env else None,
        stdout=subprocess.DEVNULL if quiet else None,
        stderr=subprocess.DEVNULL if quiet else None,
    ).returncode


def run_parallel_with_progress(
    items: list[T],
    fn: Callable[[T], None],
    max_workers: int,
    prefix: str,
    action: str,
) -> None:
    """Run fn over items in parallel with progress reporting."""
    if not items:
        return
    count = itertools.count(1)
    total = len(items)
    lock = threading.Lock()

    def worker(item: T) -> None:
        fn(item)
        with lock:
            typer.echo(f"  [{prefix}] {action} {next(count)}/{total}")

    with ThreadPoolExecutor(max_workers=min(len(items), max_workers)) as executor:
        list(executor.map(worker, items))


def ensure_dir(path: Path) -> Path:
    """Create directory and parents if needed, return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, content: str) -> None:
    """Write text content to a file, ensuring parent directory exists."""
    ensure_dir(path.parent)
    path.write_text(content)


def read_text(path: Path) -> str:
    """Read text from a file, returning empty string if not found."""
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""


def model_id_from_model(model: str) -> str:
    parts = (model or "").split("/")
    if parts and parts[-1]:
        # Replace colons and other problematic chars for filesystem paths
        return parts[-1].replace(":", "_")
    else:
        raise ValueError("Invalid model string")


def provider_env_var_from_model(model: str) -> str:
    provider = (model or "").split("/")[0]
    safe = []
    for ch in provider:
        if ch.isalnum():
            safe.append(ch.upper())
        else:
            safe.append("_")

    name = "".join(safe).strip("_")
    if name == "":
        raise ValueError("Invalid model string")
    return f"${name}_API_KEY"
