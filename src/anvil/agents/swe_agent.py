from __future__ import annotations

import os
import uuid
from pathlib import Path

from ..config import (
    default_sweagent_config_template,
    eval_dir,
    repo_root,
    swe_agent_dir,
)
from ..util import ensure_dir, model_id_from_model, provider_env_var_from_model, run


def build_image() -> int:
    """Patch swerex modal and build the SWE-agent Docker image via justfile."""
    # Apply idempotent patch: replace all "secrets" with "secret" in swerex modal.py,
    # and remove any erroneous "secret = [secret]" lines. Also update registry env names.
    modal_py = swe_agent_dir() / "swerex_patches" / "swerex" / "deployment" / "modal.py"
    if modal_py.exists():
        try:
            import re as _re

            content = modal_py.read_text()
            patched = content.replace("secrets", "secret")
            patched = patched.replace("DOCKER_USERNAME", "REGISTRY_USERNAME")
            patched = patched.replace("DOCKER_PASSWORD", "REGISTRY_PASSWORD")
            patched = _re.sub(r"\bdocker_username\b", "registry_username", patched)
            patched = _re.sub(r"\bdocker_password\b", "registry_password", patched)
            patched = _re.sub(
                r"^\s*secret\s*=\s*\[\s*secret\s*\]\s*$",
                "",
                patched,
                flags=_re.MULTILINE,
            )
            if patched != content:
                modal_py.write_text(patched)
        except Exception:
            # Best-effort patching; continue to build
            pass
    # Use the submodule's Justfile recipe to build the image
    return run(["just", "build"], cwd=swe_agent_dir())


def _load_default_sweagent_config(model: str) -> str:
    tpl = default_sweagent_config_template().read_text()
    return (
        tpl.replace("<LITELLM_MODEL_ID>", model)
        .replace("<PROVIDER_API_KEY>", provider_env_var_from_model(model))
        .replace("__EVAL_ID__", "")
    )


def init_eval(dataset_id: str, model: str) -> int:
    """Initialize eval dir and write swe-agent config."""
    eval_id = f"swe-agent_{model_id_from_model(model)}"
    ed = eval_dir(dataset_id=dataset_id, eval_id=eval_id)
    config_path = ensure_dir(ed / "sweagent_wrapper_configs") / f"{eval_id}_config.yaml"
    if not config_path.exists():
        ensure_dir(config_path.parent)
        config_path.write_text(_load_default_sweagent_config(model))
    ensure_dir(ed / "sweagent_results")
    return 0


def run_agent(dataset_id: str, model: str, config_name: str | None) -> int:
    """Run swe-agent in Docker, mounting configs and results from eval directory."""
    # Ensure Modal is configured (user logged in) since SWE-agent relies on Modal
    modal_cfg = Path.home() / ".modal.toml"
    if not modal_cfg.exists():
        return 1
    try:
        content = modal_cfg.read_text().lower()
    except Exception:
        content = ""
    if (not content) or ("token" not in content):
        return 1

    eval_id = f"swe-agent_{(model or '').split('/')[-1]}" if model else "swe-agent"
    ed = eval_dir(dataset_id=dataset_id, eval_id=eval_id)
    ensure_dir(ed / "sweagent_results")
    cfg = config_name or f"{eval_id}_config.yaml"
    tag = f"sweagent-image:{os.getlogin()}"

    prep_and_run = (
        "awk -F': ' '/repo_name:/ {print $2}' /app/sweagent_wrapper_configs/instances.yaml "
        '| tr -d "\'" '
        "| while IFS='/' read -r owner repo; do "
        '  if [ -n "$owner" ] && [ -n "$repo" ]; then '
        '    mkdir -p "/app/$owner" && ln -sfn /app "/app/$owner/$repo"; '
        "  fi; "
        "done; "
        f"python sweagent_wrapper.py {cfg}"
    )
    cmd = [
        "docker",
        "run",
        "--rm",
        "--ipc=host",
        "--name",
        f"sweagent-{os.getlogin()}-{uuid.uuid4().hex[:8]}",
        "--env-file",
        str(repo_root() / ".env"),
        "-v",
        f"{Path.home()}/.modal.toml:/root/.modal.toml",
        "-v",
        f"{swe_agent_dir() / 'config'}:/app/config",
        "-v",
        f"{ed / 'sweagent_wrapper_configs'}:/app/sweagent_wrapper_configs",
        "-v",
        f"{ed / 'sweagent_results'}:/app/sweagent_results",
        "--add-host=host.docker.internal:host-gateway",
        tag,
        "bash",
        "-lc",
        prep_and_run,
    ]
    return run(cmd, cwd=repo_root())
