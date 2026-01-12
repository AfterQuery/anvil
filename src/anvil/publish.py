"""Publish dataset images to Docker Hub."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import typer
from ruamel.yaml import YAML

from .util import run


@dataclass
class BuildTask:
    """A Docker image to build and push."""

    name: str
    dockerfile: Path
    context: Path

    def tag(self, username: str, repo: str) -> str:
        return f"{username}/{repo}:{self.name}.base"


def _docker_logged_in() -> bool:
    """Check if Docker CLI has stored credentials."""
    cfg = Path.home() / ".docker" / "config.json"
    if not cfg.exists():
        return False
    try:
        return bool(json.loads(cfg.read_text()).get("auths"))
    except Exception:
        return False


def _is_public_repo(username: str, repo: str) -> bool:
    """Check if Docker Hub repo is publicly visible. Returns False if private or unknown."""
    url = f"https://hub.docker.com/v2/repositories/{username}/{repo}/"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return not json.loads(resp.read()).get("is_private", False)
    except Exception:
        return False  # Private repos return 404, unknown is treated as safe


def _discover_build_tasks(tasks_dir: Path) -> list[BuildTask]:
    """Find Docker images to build.

    Structure:
        dockerfiles/
            docker_image_creation/<project>/  <- build contexts with source code
            base_dockerfile/<project>/        <- template Dockerfile (skip)
            base_dockerfile/<project>.task-N/ <- per-instance Dockerfile (build)
    """
    creation_dir = tasks_dir / "dockerfiles" / "docker_image_creation"
    base_df_dir = tasks_dir / "dockerfiles" / "base_dockerfile"

    if not creation_dir.exists():
        return []

    contexts = {d.name: d for d in creation_dir.iterdir() if d.is_dir()}
    tasks = []

    dockerfile_dir = base_df_dir if base_df_dir.exists() else creation_dir

    for task_dir in sorted(dockerfile_dir.iterdir()):
        dockerfile = task_dir / "Dockerfile"
        if not task_dir.is_dir() or not dockerfile.exists():
            continue

        # Skip project template dirs (exact match = template, not instance)
        if task_dir.name in contexts:
            continue

        # Instance name format: <project>.<task> -> context is <project>
        project = task_dir.name.partition(".")[0]
        context = contexts.get(project)

        if context:
            tasks.append(BuildTask(name=task_dir.name, dockerfile=dockerfile, context=context))

    return tasks


def _patch_dockerfile_if_needed(dockerfile: Path) -> str:
    """Return Dockerfile content with COPY . . inserted after FROM if missing."""
    content = dockerfile.read_text()

    if re.search(r"(?:COPY|ADD)\s+\.\s", content):
        return content

    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.strip().upper().startswith("FROM "):
            # Skip comments/blanks after FROM
            insert_at = i + 1
            while insert_at < len(lines) and (
                not lines[insert_at].strip() or lines[insert_at].strip().startswith("#")
            ):
                insert_at += 1
            lines.insert(insert_at, "WORKDIR /app")
            lines.insert(insert_at + 1, "COPY . .")
            return "\n".join(lines)

    return content


def _build_and_push(task: BuildTask, username: str, repo: str, platform: str) -> str | None:
    """Build and push a Docker image. Returns tag on success, None on failure."""
    tag = task.tag(username, repo)

    # Write patched Dockerfile to context directory (Docker buildx needs stable path)
    patched_content = _patch_dockerfile_if_needed(task.dockerfile)
    patched_dockerfile = task.context / f".Dockerfile.{task.name}"
    patched_dockerfile.write_text(patched_content)

    try:
        build_cmd = [
            "docker", "build",
            "--platform", platform,
            "-f", str(patched_dockerfile),
            "-t", tag,
            str(task.context),
        ]
        if run(build_cmd, quiet=True) != 0:
            return None

        if run(["docker", "push", tag], quiet=True) != 0:
            return None

        return tag
    finally:
        patched_dockerfile.unlink(missing_ok=True)


def _update_instances_yaml(
    inst_path: Path, built: dict[str, str], username: str, repo: str
) -> int:
    """Update instances.yaml with new image names. Returns count updated."""
    yaml = YAML()
    yaml.preserve_quotes = True

    with inst_path.open() as f:
        instances = yaml.load(f)

    updated = 0
    for inst in instances:
        iid = inst.get("instance_id", "")
        project = iid.partition(".")[0]
        # Use built tag if available, otherwise construct from instance_id
        tag = built.get(iid) or built.get(project)
        if not tag:
            # Always update to new repo even if build failed
            tag = f"{username}/{repo}:{iid}.base"
        inst["image_name"] = tag
        updated += 1

    with inst_path.open("w") as f:
        yaml.dump(instances, f)

    return updated


def publish_images(
    dataset_id: str = typer.Option(..., "--dataset", help="Dataset ID"),
    dockerhub_username: str = typer.Option(..., "--dockerhub-username", "-u", help="Docker Hub username"),
    platform: str = typer.Option("linux/amd64", "--platform", help="Docker platform"),
    repo_name: str = typer.Option("sweap-images", "--repo", help="Docker Hub repository name"),
    max_workers: int = typer.Option(4, "--max-workers", "-j", help="Max parallel builds (lower to avoid rate limits)"),
) -> None:
    """Build and push dataset images to your private Docker Hub."""
    tasks_dir = Path(dataset_id) / "tasks"

    if not _docker_logged_in():
        typer.echo("Not logged into Docker. Run `docker login` first.", err=True)
        raise typer.Exit(1)

    if _is_public_repo(dockerhub_username, repo_name):
        typer.echo(f"Repository {dockerhub_username}/{repo_name} is PUBLIC. Refusing to push.", err=True)
        raise typer.Exit(1)

    build_tasks = _discover_build_tasks(tasks_dir)
    if not build_tasks:
        typer.echo(f"No Dockerfiles found in {tasks_dir}/dockerfiles/", err=True)
        raise typer.Exit(1)

    typer.echo(f"Building {len(build_tasks)} image(s)...")

    built: dict[str, str] = {}
    failed: list[str] = []

    with ThreadPoolExecutor(max_workers=min(len(build_tasks), max_workers)) as executor:
        futures = {
            executor.submit(_build_and_push, task, dockerhub_username, repo_name, platform): task
            for task in build_tasks
        }

        for i, future in enumerate(as_completed(futures), 1):
            task = futures[future]
            try:
                tag = future.result()
                if tag:
                    typer.echo(f"[{i}/{len(build_tasks)}] {task.name} ✓")
                    built[task.name] = tag
                else:
                    typer.echo(f"[{i}/{len(build_tasks)}] {task.name} ✗", err=True)
                    failed.append(task.name)
            except Exception as e:
                typer.echo(f"[{i}/{len(build_tasks)}] {task.name} ✗ ({e})", err=True)
                failed.append(task.name)

    if not built:
        typer.echo("All builds failed", err=True)
        raise typer.Exit(1)

    inst_path = tasks_dir / "instances.yaml"
    if inst_path.exists():
        updated = _update_instances_yaml(inst_path, built, dockerhub_username, repo_name)
        typer.echo(f"Updated {updated} instance(s) in instances.yaml")
    else:
        typer.echo(f"{inst_path} not found, skipping update", err=True)

    if failed:
        typer.echo(f"Failed: {', '.join(failed)}", err=True)
        raise typer.Exit(1)
