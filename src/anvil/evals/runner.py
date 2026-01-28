"""Main evaluation runner for anvil.

This module orchestrates running agents on datasets and evaluating their output.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import typer
from ruamel.yaml import YAML

from ..agents.harness import (
    AGENT_CONFIGS,
    AgentResult,
    load_instances,
    run_agent_in_modal,
    write_single_result,
)
from ..config import eval_output_dir, swe_bench_eval_script, tasks_dir
from ..util import ensure_dir, model_id_from_model, provider_env_var_from_model
from .pass_at_k import (
    compute_pass_at_k_summary,
    print_pass_at_k_summary,
    save_pass_at_k_json,
)


def _eval_id(agent: str, model: str) -> str:
    """Compose eval_id as '<agent>_<model-suffix>'."""
    # Oracle agent doesn't use a model
    if agent == "oracle":
        return agent
    base = model_id_from_model(model)
    return f"{agent}_{base}" if agent else base


def _get_completed_rollouts(
    base_out: Path, instances: list[dict], k: int
) -> set[tuple[str, int]]:
    """Return set of (instance_id, attempt) pairs that have valid completed rollouts."""
    completed = set()
    for inst in instances:
        iid = inst["instance_id"]
        for attempt in range(1, k + 1):
            meta_path = (
                base_out / iid / f"attempt_{attempt}" / "rollout" / "metadata.json"
            )
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                    if meta.get("exit_code") == 0 and meta.get("error") is None:
                        completed.add((iid, attempt))
                except (json.JSONDecodeError, OSError):
                    pass
    return completed


def _get_completed_evals(
    base_out: Path, instances: list[dict], k: int, eval_id: str
) -> set[tuple[str, int]]:
    """Return set of (instance_id, attempt) pairs that have valid completed evals."""
    completed = set()
    for inst in instances:
        iid = inst["instance_id"]
        for attempt in range(1, k + 1):
            results_path = (
                base_out
                / iid
                / f"attempt_{attempt}"
                / "eval_results"
                / "eval_results.json"
            )
            if results_path.exists():
                try:
                    json.loads(results_path.read_text())
                    completed.add((iid, attempt))
                except (json.JSONDecodeError, OSError):
                    pass
    return completed


def _cleanup_bad_rollouts(base_out: Path, instances: list[dict], k: int) -> int:
    """Move bad rollouts to __errors/ folder. Returns count moved."""
    errors_dir = base_out / "__errors"
    moved = 0

    for inst in instances:
        iid = inst["instance_id"]
        for attempt in range(1, k + 1):
            attempt_dir = base_out / iid / f"attempt_{attempt}"
            meta_path = attempt_dir / "rollout" / "metadata.json"

            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                    if meta.get("exit_code") != 0 or meta.get("error") is not None:
                        dst = errors_dir / iid / f"attempt_{attempt}"
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.move(str(attempt_dir), str(dst))
                        moved += 1
                except (json.JSONDecodeError, OSError):
                    pass

    return moved


def _cleanup_bad_evals(
    base_out: Path, instances: list[dict], k: int, eval_id: str
) -> int:
    """Move bad eval results to __errors/ folder. Returns count moved."""
    errors_dir = base_out / "__errors"
    moved = 0

    for inst in instances:
        iid = inst["instance_id"]
        for attempt in range(1, k + 1):
            eval_dir = base_out / iid / f"attempt_{attempt}" / "eval_results"
            results_path = eval_dir / "eval_results.json"

            if eval_dir.exists() and not results_path.exists():
                dst = errors_dir / iid / f"attempt_{attempt}" / "eval_results"
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.move(str(eval_dir), str(dst))
                moved += 1

    return moved


def run_evaluation(
    model: str | None,
    dataset_id: str,
    dockerhub_username: str,
    dockerhub_repo: str,
    agent: str = "mini-swe-agent",
    n_attempts: int = 1,
    output: str | None = None,
    max_wait_minutes: int | None = None,
    max_parallel: int = 30,
    no_continue: bool = False,
) -> int:
    """Run full evaluation with an agent on a dataset."""
    from tqdm import tqdm

    # Load .env early for credential check
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parents[3] / ".env")
    except ImportError:
        pass

    # Oracle agent doesn't need a model
    if agent == "oracle":
        model = model or "oracle"
    elif not model:
        typer.echo("Error: --model is required for non-oracle agents")
        return 1

    # Validate registry credentials upfront - required for both agent runs and evals
    reg_user = os.environ.get("REGISTRY_USERNAME")
    reg_pass = os.environ.get("REGISTRY_PASSWORD")
    if not reg_user or not reg_pass:
        typer.echo("Error: REGISTRY_USERNAME and REGISTRY_PASSWORD must be set")
        typer.echo("")
        typer.echo("These credentials are required to pull Docker images from Docker Hub.")
        typer.echo("Set them in your environment or in a .env file at the repo root:")
        typer.echo("")
        typer.echo("  export REGISTRY_USERNAME=your_dockerhub_username")
        typer.echo("  export REGISTRY_PASSWORD=your_dockerhub_access_token")
        typer.echo("")
        typer.echo("You can create an access token at https://hub.docker.com/settings/security")
        return 1

    k = n_attempts
    
    # Validate k
    if k < 1:
        typer.echo("Error: --n-attempts must be at least 1")
        return 1

    # Default max wait = 10 minutes * k / 2 (e.g., k=5 -> 25 min)
    if max_wait_minutes is None:
        max_wait_minutes = max(10, 10 * k // 2)

    start_time = time.time()
    eval_id = _eval_id(agent, model)
    base_out_path = Path(output) if output else eval_output_dir(dataset_id, eval_id)
    
    # Handle --no-continue: delete existing results directory
    if no_continue and base_out_path.exists():
        shutil.rmtree(base_out_path)
        typer.echo(f"Deleted existing results: {base_out_path}")
    
    base_out = ensure_dir(base_out_path)
    instances = load_instances(dataset_id)
    n_tasks = len(instances)
    dataset_tasks_dir = tasks_dir(dataset_id)

    typer.echo(f"Running {agent} evaluation on {dataset_id}")
    typer.echo(f"  Model: {model}")
    typer.echo(f"  Tasks: {n_tasks}")
    typer.echo(f"  Attempts: {k}")
    typer.echo(f"  Output: {base_out}")

    # ---- Oracle: skip rollout, use gold_patches.json directly ----
    if agent == "oracle":
        gold_patches_path = dataset_tasks_dir / "gold_patches.json"
        if not gold_patches_path.exists():
            typer.echo(f"Error: gold_patches.json not found at {gold_patches_path}")
            return 1

        gold_patches = json.loads(gold_patches_path.read_text())
        typer.echo(f"Loaded {len(gold_patches)} golden patches")

        # Build patches for eval, add attempt=1
        bad_eval_moved = _cleanup_bad_evals(base_out, instances, k, eval_id)
        completed_evals = _get_completed_evals(base_out, instances, k, eval_id)

        all_patches = []
        for p in gold_patches:
            iid = p["instance_id"]
            if (iid, 1) not in completed_evals:
                all_patches.append({
                    "instance_id": iid,
                    "patch": p.get("patch", ""),
                    "prefix": eval_id,
                    "attempt": 1,
                })
    else:
        # ---- Non-oracle: run agent rollouts ----
        bad_moved = _cleanup_bad_rollouts(base_out, instances, k)
        completed_rollouts = _get_completed_rollouts(base_out, instances, k)

        work_items: list[tuple[dict, int]] = []
        for inst in instances:
            iid = inst["instance_id"]
            for attempt in range(1, k + 1):
                if (iid, attempt) not in completed_rollouts:
                    work_items.append((inst, attempt))

        total_runs = n_tasks * k
        remaining_runs = len(work_items)
        complete_runs = total_runs - remaining_runs

        if remaining_runs == 0:
            typer.echo(f"Rollouts: {complete_runs}/{total_runs} complete, nothing to run")
        else:
            status = f"Rollouts: {complete_runs}/{total_runs} complete, running {remaining_runs}"
            if bad_moved > 0:
                status += f" ({bad_moved} bad moved to __errors/)"
            typer.echo(status)

            agent_config = AGENT_CONFIGS[agent]
            provider_env = provider_env_var_from_model(model)
            keep_n = min(k, 10)

            results_by_instance: dict[str, list[AgentResult | None]] = {
                i["instance_id"]: [None] * k for i in instances
            }

            async def run_all_agents():
                import modal

                modal.enable_output()
                os.environ.setdefault("MODAL_MAX_THROTTLE_WAIT", str(max_wait_minutes * 60))

                app = modal.App.lookup("anvil-agent-harness", create_if_missing=True)

                registry_secret = None
                if os.environ.get("REGISTRY_USERNAME") and os.environ.get("REGISTRY_PASSWORD"):
                    registry_secret = modal.Secret.from_dict({
                        "REGISTRY_USERNAME": os.environ["REGISTRY_USERNAME"],
                        "REGISTRY_PASSWORD": os.environ["REGISTRY_PASSWORD"],
                    })

                semaphore = asyncio.Semaphore(max_parallel)
                pbar = tqdm(total=remaining_runs, desc="Agent runs", unit="run", file=sys.stderr)

                async def run_one(inst: dict, attempt: int) -> AgentResult:
                    async with semaphore:
                        result = await run_agent_in_modal(
                            agent_config=agent_config,
                            instance=inst,
                            model=model,
                            provider_env_var=provider_env,
                            app=app,
                            registry_secret=registry_secret,
                        )

                        iid = result.instance_id
                        results_by_instance[iid][attempt - 1] = result

                        if attempt <= keep_n:
                            result_dir = base_out / iid / f"attempt_{attempt}" / "rollout"
                            write_single_result(result, result_dir, eval_id)

                        status = "ok" if result.exit_code == 0 and not result.error else "fail"
                        pbar.set_postfix_str(f"{iid}:{attempt} {status}")
                        pbar.update(1)

                        return result

                tasks = [
                    asyncio.create_task(run_one(inst, attempt))
                    for inst, attempt in work_items
                ]
                await asyncio.gather(*tasks)
                pbar.close()

            typer.echo(f"Running agents (max {max_parallel} parallel)...")
            asyncio.run(run_all_agents())

        # ---- Evaluation Phase for non-oracle ----
        bad_eval_moved = _cleanup_bad_evals(base_out, instances, k, eval_id)
        completed_evals = _get_completed_evals(base_out, instances, k, eval_id)

        all_patches = []
        for inst in instances:
            iid = inst["instance_id"]
            for attempt in range(1, k + 1):
                if (iid, attempt) in completed_evals:
                    continue

                pred_path = base_out / iid / f"attempt_{attempt}" / "rollout" / f"{iid}.pred"
                patch = ""
                if pred_path.exists():
                    try:
                        pred_data = json.loads(pred_path.read_text())
                        patch = pred_data.get("model_patch", "")
                    except (json.JSONDecodeError, OSError):
                        pass

                all_patches.append({
                "instance_id": iid,
                "patch": patch,
                "prefix": eval_id,
                "attempt": attempt,
            })

    total_evals = n_tasks * k
    remaining_evals = len(all_patches)
    complete_evals = total_evals - remaining_evals

    if remaining_evals == 0:
        typer.echo(f"Evals: {complete_evals}/{total_evals} complete, nothing to run")
    else:
        eval_status = f"Evals: {complete_evals}/{total_evals} complete, running {remaining_evals}"
        if bad_eval_moved > 0:
            eval_status += f" ({bad_eval_moved} bad moved to __errors/)"
        typer.echo(eval_status)

    if all_patches:
        patches_file = base_out / f"{eval_id}_all_patches.json"
        patches_file.write_text(json.dumps(all_patches, indent=2))

        eval_workers = min(len(all_patches), max_parallel)

        cmd = [
            "uv",
            "run",
            str(swe_bench_eval_script()),
            f"--raw_sample_path={dataset_tasks_dir / 'tasks.csv'}",
            f"--patch_path={patches_file}",
            f"--output_dir={base_out}",
            f"--scripts_dir={ensure_dir(dataset_tasks_dir / 'run_scripts')}",
            f"--num_workers={eval_workers}",
            f"--dockerhub_username={dockerhub_username}",
            f"--dockerhub_repo={dockerhub_repo}",
        ]

        # Pass environment variables (including REGISTRY_USERNAME/PASSWORD) to subprocess
        result = subprocess.run(
            cmd,
            cwd=str(dataset_tasks_dir),
            env=os.environ.copy(),
        )

        patches_file.unlink(missing_ok=True)
        
        if result.returncode != 0:
            return 1

    # ---- Aggregate Results ----
    results_file = base_out / "eval_results.json"
    all_results = json.loads(results_file.read_text()) if results_file.exists() else {}

    eval_results: dict[str, list[bool]] = {i["instance_id"]: [] for i in instances}
    for inst in instances:
        iid = inst["instance_id"]
        for attempt in range(1, k + 1):
            key = f"{iid}:attempt_{attempt}"
            if key in all_results:
                eval_results[iid].append(all_results[key])
            else:
                task_result_path = (
                    base_out / iid / f"attempt_{attempt}" / "eval_results" / "eval_results.json"
                )
                if task_result_path.exists():
                    try:
                        task_result = json.loads(task_result_path.read_text())
                        eval_results[iid].append(task_result.get(iid, False))
                    except (json.JSONDecodeError, OSError):
                        eval_results[iid].append(False)
                else:
                    eval_results[iid].append(False)

    # Report per-attempt results
    for attempt in range(1, k + 1):
        passed = sum(
            1 for r in eval_results.values() if len(r) >= attempt and r[attempt - 1]
        )
        typer.echo(f"  Attempt {attempt}: {passed}/{n_tasks} passed")

    summary = compute_pass_at_k_summary(
        eval_results, model, dataset_id, agent, k, time.time() - start_time
    )
    print_pass_at_k_summary(summary)
    save_pass_at_k_json(summary, base_out / "eval_results_pass_at_k.json")
    
    return 0 if any(r.solved for r in summary.per_instance) else 1
