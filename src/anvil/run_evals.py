"""Run evaluations on a dataset."""

from __future__ import annotations

from typing import Annotated, Literal

import typer


def run_evals(
    model: str = typer.Option(
        ..., "--model", help="Model ID (litellm-compatible, e.g., openrouter/google/gemini-3-flash-preview)"
    ),
    dataset: str = typer.Option(..., "--dataset", help="Dataset ID or path"),
    agent: Annotated[
        Literal["mini-swe-agent"],
        typer.Option("--agent", help="Agent to use for evaluation"),
    ] = "mini-swe-agent",
    n_attempts: Annotated[
        int,
        typer.Option(
            "--n-attempts", "-n", help="Number of attempts per task for pass@k evaluation"
        ),
    ] = 1,
    max_wait: Annotated[
        int | None,
        typer.Option(
            "--max-wait",
            help="Max minutes to wait for Modal rate limits",
        ),
    ] = None,
    max_parallel: Annotated[
        int,
        typer.Option(
            "--max-parallel",
            help="Max concurrent runs",
        ),
    ] = 30,
    no_continue: Annotated[
        bool,
        typer.Option(
            "--no-continue",
            help="Start fresh instead of resuming",
        ),
    ] = False,
    output: str | None = typer.Option(
        None, "--output", help="Output directory override"
    ),
    dockerhub_username: str = typer.Option(
        ..., "--dockerhub-username", help="DockerHub username"
    ),
    dockerhub_repo: str = typer.Option(
        ..., "--dockerhub-repo", help="DockerHub repo name"
    ),
) -> None:
    """Run evaluation with an agent on a dataset."""
    from .evals import run_evaluation

    rc = run_evaluation(
        model=model,
        dataset_id=dataset,
        dockerhub_username=dockerhub_username,
        dockerhub_repo=dockerhub_repo,
        agent=agent,
        n_attempts=n_attempts,
        output=output,
        max_wait_minutes=max_wait,
        max_parallel=max_parallel,
        no_continue=no_continue,
    )
    raise typer.Exit(rc)
