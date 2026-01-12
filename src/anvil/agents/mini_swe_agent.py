"""Mini-SWE-Agent integration using Modal-based harness.

This module provides a simplified interface for running mini-swe-agent
on Modal sandboxes with parallel execution support.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from ..config import default_minisweagent_config_template, eval_dir
from ..util import ensure_dir, model_id_from_model, provider_env_var_from_model
from .harness import (
    AGENT_CONFIGS,
    load_instances,
    run_agents_batch,
    write_results,
    write_single_result,
)


def _load_default_minisweagent_config(model: str) -> str:
    """Load and configure mini-swe-agent config template."""
    tpl = default_minisweagent_config_template().read_text()
    return tpl.replace("<LITELLM_MODEL_ID>", model).replace(
        "<PROVIDER_API_KEY>", provider_env_var_from_model(model)
    )


def init_eval(dataset_id: str, model: str) -> int:
    """Initialize evaluation directory structure."""
    eval_id = f"mini-swe-agent_{model_id_from_model(model)}"
    ed = eval_dir(dataset_id=dataset_id, eval_id=eval_id)
    config_path = ensure_dir(ed / "minisweagent_configs") / f"{eval_id}_config.yaml"
    if not config_path.exists():
        ensure_dir(config_path.parent)
        config_path.write_text(_load_default_minisweagent_config(model))
    ensure_dir(ed / "results")
    return 0


def run_dataset_batch(
    model: str,
    dataset_id: str,
    base_output: Path | None = None,
) -> int:
    """Run mini-swe-agent on all instances in a dataset using Modal.

    Modal handles concurrency and rate limiting internally via MODAL_MAX_THROTTLE_WAIT.

    Args:
        model: Model identifier (e.g., "openai/gpt-4")
        dataset_id: Dataset identifier
        base_output: Optional output directory override

    Returns:
        0 on success, 1 on failure
    """
    import modal

    # Load instances
    instances = load_instances(dataset_id)
    typer.echo(f"Loaded {len(instances)} instances from {dataset_id}")

    # Get agent config
    agent_config = AGENT_CONFIGS["mini-swe-agent"]

    # Setup output directory
    eval_id = f"mini-swe-agent_{model_id_from_model(model)}"
    output_dir = (
        ensure_dir(base_output)
        if base_output
        else ensure_dir(eval_dir(dataset_id=dataset_id, eval_id=eval_id))
    )

    # Get provider env var
    provider_env_var = provider_env_var_from_model(model)

    # Progress callback
    def on_progress(instance_id: str, status: str) -> None:
        typer.echo(f"  [{status}] {instance_id}")

    # Write each result immediately as it completes (task-first structure)
    def on_result(result) -> None:
        result_dir = output_dir / result.instance_id / "attempt_1"
        write_single_result(result, result_dir, eval_id)

    typer.echo(f"Running {len(instances)} instances...")

    # Run agents in parallel on Modal - Modal handles concurrency/throttling internally
    with modal.enable_output():
        results = asyncio.run(
            run_agents_batch(
                agent_config=agent_config,
                instances=instances,
                model=model,
                provider_env_var=provider_env_var,
                on_progress=on_progress,
                on_result=on_result,
            )
        )

    # Write aggregated patches JSON (individual results already written by on_result)
    write_results(results, output_dir, eval_id)

    # Summarize
    succeeded = sum(1 for r in results if r.exit_code == 0)
    failed = len(results) - succeeded

    typer.echo(f"\nResults: {succeeded} succeeded, {failed} failed")
    typer.echo(f"Output: {output_dir}")

    if failed > 0:
        typer.echo("\nFailed instances:")
        for r in results:
            if r.exit_code != 0:
                error_msg = r.error or f"exit code {r.exit_code}"
                typer.echo(f"  - {r.instance_id}: {error_msg}")

    return 0 if failed == 0 else 1
