"""Pass@k metric computation utilities."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import typer


def estimate_pass_at_k(n: int, c: int, k: int) -> float:
    """Compute pass@k = 1 - C(n-c, k) / C(n, k)."""
    if n < k:
        return 1.0 if c > 0 else 0.0
    if c == 0:
        return 0.0
    if c >= n:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


@dataclass
class PassAtKResult:
    instance_id: str
    attempts: int
    successes: int
    pass_at_1: float
    pass_at_k: float
    solved: bool


@dataclass
class PassAtKSummary:
    model: str
    dataset: str
    agent: str
    k: int
    n_tasks: int
    total_runs: int
    duration_seconds: float
    aggregate_pass_at_1: float
    aggregate_pass_at_k: float
    per_instance: list[PassAtKResult]


def compute_pass_at_k_summary(
    results_by_instance: dict[str, list[bool]],
    model: str,
    dataset: str,
    agent: str,
    k: int,
    duration_seconds: float,
) -> PassAtKSummary:
    per_instance = []
    for instance_id, results in sorted(results_by_instance.items()):
        n, c = len(results), sum(results)
        per_instance.append(
            PassAtKResult(
                instance_id=instance_id,
                attempts=n,
                successes=c,
                pass_at_1=estimate_pass_at_k(n, c, 1),
                pass_at_k=estimate_pass_at_k(n, c, k),
                solved=c > 0,
            )
        )

    n_tasks = len(per_instance)
    return PassAtKSummary(
        model=model,
        dataset=dataset,
        agent=agent,
        k=k,
        n_tasks=n_tasks,
        total_runs=sum(r.attempts for r in per_instance),
        duration_seconds=duration_seconds,
        aggregate_pass_at_1=sum(r.pass_at_1 for r in per_instance) / n_tasks
        if n_tasks
        else 0.0,
        aggregate_pass_at_k=sum(r.pass_at_k for r in per_instance) / n_tasks
        if n_tasks
        else 0.0,
        per_instance=per_instance,
    )


def print_pass_at_k_summary(summary: PassAtKSummary) -> None:
    echo = typer.echo
    m, s = divmod(int(summary.duration_seconds), 60)

    echo("")
    echo("═" * 75)
    echo("                         EVALUATION RESULTS")
    echo("═" * 75)
    echo(f"  Model:       {summary.model}")
    echo(f"  Dataset:     {summary.dataset}")
    echo(f"  Agent:       {summary.agent}")
    echo(f"  Tasks:       {summary.n_tasks}")
    echo(f"  Attempts:    k={summary.k} ({summary.total_runs} runs, {m}m {s}s)")
    echo("")
    echo("─" * 75)
    echo(f"  pass@1:    {summary.aggregate_pass_at_1:5.1%}")
    if summary.k > 1:
        solved = sum(1 for r in summary.per_instance if r.solved)
        echo(
            f"  pass@{summary.k}:    {summary.aggregate_pass_at_k:5.1%}   ({solved}/{summary.n_tasks} solved)"
        )
    echo("")
    echo("─" * 75)
    if summary.k > 1:
        echo(
            f"  {'Task':<40} {'Result':<12} {'pass@1':<8} {'pass@' + str(summary.k):<8}"
        )
    else:
        echo(f"  {'Task':<40} {'Result':<12} {'pass@1':<8}")
    echo("  " + "─" * 71)

    def _sort_key(x):
        parts = x.instance_id.rsplit(".", 1)
        repo = parts[0] if len(parts) > 1 else x.instance_id
        match = re.search(r"(\d+)$", x.instance_id)
        task_num = int(match.group(1)) if match else 0
        return (-x.successes, repo, task_num)

    for r in sorted(summary.per_instance, key=_sort_key):
        name = (r.instance_id[:38] + "..") if len(r.instance_id) > 40 else r.instance_id
        fill_count = round(5 * r.successes / r.attempts) if r.attempts > 0 else 0
        bar = "█" * fill_count + "░" * (5 - fill_count)
        status = "✓" if r.solved else "✗"
        if summary.k > 1:
            echo(
                f"  {name:<40} {bar} {r.successes}/{r.attempts:<5} {r.pass_at_1:5.0%}    {r.pass_at_k:5.0%}    {status}"
            )
        else:
            echo(
                f"  {name:<40} {bar} {r.successes}/{r.attempts:<5} {r.pass_at_1:5.0%}    {status}"
            )

    echo("═" * 75)


def save_pass_at_k_json(summary: PassAtKSummary, output_path: Path) -> None:
    data = {
        "metadata": {
            "model": summary.model,
            "dataset": summary.dataset,
            "agent": summary.agent,
            "k": summary.k,
            "n_tasks": summary.n_tasks,
            "total_runs": summary.total_runs,
            "duration_seconds": summary.duration_seconds,
        },
        "aggregate": {
            "pass_at_1": summary.aggregate_pass_at_1,
            f"pass_at_{summary.k}": summary.aggregate_pass_at_k,
        },
        "per_instance": {
            r.instance_id: {
                "attempts": r.attempts,
                "successes": r.successes,
                "pass_at_1": r.pass_at_1,
                f"pass_at_{summary.k}": r.pass_at_k,
                "solved": r.solved,
            }
            for r in summary.per_instance
        },
    }
    output_path.write_text(json.dumps(data, indent=2))
    typer.echo(f"Results: {output_path}")
