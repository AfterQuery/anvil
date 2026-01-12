"""Evaluate SWE-bench Pro patches using Modal or local Docker.

This file is adapted from the SWE-bench Pro OS repository:
https://github.com/scaleapi/SWE-bench_Pro-os

This evaluation script:
1. Takes a CSV file containing test cases and a JSON file containing patches
2. Runs each patch in a Modal sandbox environment using Docker Hub images
3. Executes the tests using local run scripts and collects results
4. Calculates overall accuracy based on test pass/fail status

Usage:
python swe_bench_pro_eval.py \
    --raw_sample_path=data.csv \
    --patch_path={OUTPUT}/gold_patches.json \
    --output_dir={OUTPUT}/ \
    --scripts_dir=run_scripts \
    --num_workers=100 \
    --dockerhub_username=your-username
"""

import argparse
import concurrent.futures
import json
import os
import platform as py_platform
import sys

try:
    import modal
except Exception:
    modal = None
try:
    import docker
except Exception:
    docker = None
import pandas as pd
from tqdm import tqdm


# ---- Inlined from helper_code/image_uri.py ----

def get_dockerhub_image_uri(uid: str, dockerhub_username: str, dockerhub_repo: str, repo_name: str = "") -> str:
    """Convert instance_id and repo name to Docker Hub image URI."""
    if repo_name:
        try:
            repo_base, repo_name_only = repo_name.lower().split("/", 1)
        except ValueError:
            repo_base = repo_name.lower()
            repo_name_only = repo_name.lower()
        hsh = uid.replace("instance_", "")
        tag = f"{repo_base}.{repo_name_only}-{hsh}"
    else:
        if "__" in uid and len(uid) > 9:
            tag_part = uid[9:]
        else:
            tag_part = uid
        tag = f"default-{tag_part}"

    if len(tag) > 128:
        tag = tag[:128]

    return f"{dockerhub_username}/{dockerhub_repo}:{tag}"


# ---- Docker helpers ----

def load_base_docker(iid):
    with open(f"dockerfiles/base_dockerfile/{iid}/Dockerfile") as fp:
        return fp.read()


def instance_docker(iid):
    with open(f"dockerfiles/instance_dockerfile/{iid}/Dockerfile") as fp:
        return fp.read()


def load_local_script(scripts_dir, instance_id, script_name):
    script_path = os.path.join(scripts_dir, instance_id, script_name)
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script not found: {script_path}")
    with open(script_path, "r") as f:
        return f.read()


def create_entryscript(sample):
    before_repo_set_cmd = sample["before_repo_set_cmd"].strip().split("\n")[-1]
    selected_test_files_to_run = ",".join(eval(sample["selected_test_files_to_run"]))
    base_commit = sample["base_commit"]
    base_dockerfile = load_base_docker(sample["instance_id"])
    instance_dockerfile = instance_docker(sample["instance_id"])

    env_cmds = []
    for dockerfile_content in [base_dockerfile, instance_dockerfile]:
        for line in dockerfile_content.split("\n"):
            line = line.strip()
            if line.startswith("ENV"):
                env_cmd = line.replace("ENV", "export", 1)
                env_cmds.append(env_cmd)

    env_cmds = "\n".join(env_cmds)

    entry_script = f"""
{env_cmds}
cd /app
git reset --hard {base_commit}
git checkout {base_commit}
git apply -v --ignore-whitespace /workspace/patch.diff 2>&1 || \\
patch -p1 --forward --reject-file=- --no-backup-if-mismatch < /workspace/patch.diff 2>&1 || true
{before_repo_set_cmd}
bash /workspace/run_script.sh {selected_test_files_to_run} > /workspace/stdout.log 2> /workspace/stderr.log
python3 /workspace/parser.py /workspace/stdout.log /workspace/stderr.log /workspace/output.json
"""
    return entry_script


def create_dockerhub_tag(uid, repo_name=""):
    if repo_name:
        repo_base, repo_name_only = repo_name.lower().split("/")
        hsh = uid.replace("instance_", "")
        return f"{repo_base}.{repo_name_only}-{hsh}"
    else:
        image_name = "default"

    if "__" in uid and len(uid) > 9:
        tag_part = uid[9:]
    else:
        tag_part = uid

    return f"{image_name}-{tag_part}"


def prepare_run(uid, output_dir, prefix, redo, attempt=None):
    if attempt is not None:
        uid_dir = os.path.join(output_dir, uid, f"attempt_{attempt}", "eval_results")
    else:
        uid_dir = os.path.join(output_dir, uid)
    os.makedirs(uid_dir, exist_ok=True)
    output_path = os.path.join(uid_dir, f"{prefix}_output.json")
    if not redo and os.path.exists(output_path):
        with open(output_path, "r") as f:
            return (
                json.load(f),
                output_path,
                os.path.join(uid_dir, "workspace"),
                uid_dir,
            )
    workspace_dir = os.path.join(uid_dir, "workspace")
    os.makedirs(workspace_dir, exist_ok=True)
    return None, output_path, workspace_dir, uid_dir


def write_patch_snapshot(uid_dir, prefix, patch):
    with open(os.path.join(uid_dir, f"{prefix}_patch.diff"), "w") as f:
        f.write(patch)


def assemble_workspace_files(uid, scripts_dir, patch, sample):
    run_script = load_local_script(scripts_dir, uid, "run_script.sh")
    parser_script = load_local_script(scripts_dir, uid, "parser.py")
    entryscript_content = create_entryscript(sample)

    files = {
        "patch.diff": patch,
        "run_script.sh": run_script,
        "parser.py": parser_script,
        "entryscript.sh": entryscript_content,
    }
    return files, entryscript_content


def write_files_modal(sandbox, files):
    for rel_path, content in files.items():
        with sandbox.open(f"/workspace/{rel_path}", "w") as f:
            f.write(content)


def write_files_local(workspace_dir, files):
    for rel_path, content in files.items():
        dst = os.path.join(workspace_dir, rel_path)
        with open(dst, "w") as f:
            f.write(content)


def save_entryscript_copy(uid_dir, prefix, entryscript_content):
    with open(os.path.join(uid_dir, f"{prefix}_entryscript.sh"), "w") as f:
        f.write(entryscript_content if entryscript_content is not None else "")


def collect_outputs_modal(sandbox, uid_dir, uid, prefix):
    try:
        with sandbox.open("/workspace/stdout.log", "r") as f_in:
            with open(os.path.join(uid_dir, f"{prefix}_stdout.log"), "w") as f:
                stdout_content = f_in.read()
                f.write(stdout_content if stdout_content is not None else "")
    except FileNotFoundError:
        pass
    try:
        with sandbox.open("/workspace/stderr.log", "r") as f_in:
            with open(os.path.join(uid_dir, f"{prefix}_stderr.log"), "w") as f:
                stderr_content = f_in.read()
                f.write(stderr_content if stderr_content is not None else "")
    except FileNotFoundError:
        pass

    try:
        with sandbox.open("/workspace/output.json", "r") as f_in:
            output = json.load(f_in)
            with open(os.path.join(uid_dir, f"{prefix}_output.json"), "w") as f:
                json.dump(output, f)
            return output
    except FileNotFoundError:
        print(f"Warning: output.json not found for {uid}")
        return None


def collect_outputs_local(workspace_dir, uid_dir, uid, prefix):
    def _copy_safe(src_name, dest_name):
        src_path = os.path.join(workspace_dir, src_name)
        dest_path = os.path.join(uid_dir, dest_name)
        try:
            with open(src_path, "r") as f_in:
                content = f_in.read()
        except FileNotFoundError:
            content = ""
        with open(dest_path, "w") as f_out:
            f_out.write(content if content is not None else "")

    _copy_safe("stdout.log", f"{prefix}_stdout.log")
    _copy_safe("stderr.log", f"{prefix}_stderr.log")

    try:
        with open(os.path.join(workspace_dir, "output.json"), "r") as f_in:
            output = json.load(f_in)
            with open(os.path.join(uid_dir, f"{prefix}_output.json"), "w") as f:
                json.dump(output, f)
            return output
    except FileNotFoundError:
        print(f"Warning: output.json not found for {uid}")
        return None


def eval_with_modal(
    patch, sample, output_dir, dockerhub_username, scripts_dir, dockerhub_repo,
    prefix="", redo=False, block_network=False, docker_platform=None, attempt=None,
):
    if modal is None:
        raise RuntimeError("modal is not installed")
    uid = sample["instance_id"]
    existing_output, output_path, workspace_dir, uid_dir = prepare_run(
        uid, output_dir, prefix, redo, attempt=attempt
    )
    if existing_output is not None:
        return existing_output

    sandbox = None
    
    try:
        write_patch_snapshot(uid_dir, prefix, patch)
        files, entryscript_content = assemble_workspace_files(uid, scripts_dir, patch, sample)

        app = modal.App.lookup(name="anvil-swe-bench-eval", create_if_missing=True)
        
        # Use image_name from instances.yaml if available, otherwise construct it
        if "image_name" in sample and sample["image_name"]:
            dockerhub_image_uri = sample["image_name"]
        else:
            dockerhub_image_uri = get_dockerhub_image_uri(uid, dockerhub_username, dockerhub_repo, sample.get("repo", ""))

        # Registry credentials for private Docker Hub images
        registry_secret = None
        if os.environ.get("REGISTRY_USERNAME") and os.environ.get("REGISTRY_PASSWORD"):
            registry_secret = modal.Secret.from_dict({
                "REGISTRY_USERNAME": os.environ["REGISTRY_USERNAME"],
                "REGISTRY_PASSWORD": os.environ["REGISTRY_PASSWORD"],
            })

        image = modal.Image.from_registry(
            dockerhub_image_uri, secret=registry_secret,
        ).dockerfile_commands(['CMD ["sleep", "infinity"]'])

        sandbox = modal.Sandbox.create(
            image=image, app=app, timeout=60 * 60,
            cpu=(1, 4), memory=(5 * 1024, 30 * 1024), block_network=block_network,
        )

        process = sandbox.exec("mkdir", "-p", "/workspace")
        process.wait()
        write_files_modal(sandbox, files)
        process = sandbox.exec("bash", "/workspace/entryscript.sh")
        process.wait()

        if process.returncode != 0:
            print(f"Entryscript failed for {uid} with return code: {process.returncode}")

        output = collect_outputs_modal(sandbox, uid_dir, uid, prefix)
        if output is None:
            return None
        save_entryscript_copy(uid_dir, prefix, entryscript_content)
        return output
    except Exception as e:
        print(f"Error evaluating {uid}: {e}")
        raise
    finally:
        if sandbox:
            try:
                sandbox.terminate()
            except Exception:
                pass


def eval_with_docker(
    patch, sample, output_dir, dockerhub_username, scripts_dir, dockerhub_repo,
    prefix="", redo=False, block_network=False, docker_platform=None, attempt=None,
):
    if docker is None:
        raise RuntimeError("docker SDK is not installed")
    uid = sample["instance_id"]
    existing_output, output_path, workspace_dir, uid_dir = prepare_run(
        uid, output_dir, prefix, redo, attempt=attempt
    )
    if existing_output is not None:
        return existing_output

    try:
        files, entryscript_content = assemble_workspace_files(uid, scripts_dir, patch, sample)
        write_files_local(workspace_dir, files)
        write_patch_snapshot(uid_dir, prefix, patch)

        # Use image_name from instances.yaml if available, otherwise construct it
        if "image_name" in sample and sample["image_name"]:
            dockerhub_image_uri = sample["image_name"]
        else:
            dockerhub_image_uri = get_dockerhub_image_uri(uid, dockerhub_username, dockerhub_repo, sample.get("repo", ""))

        client = docker.from_env()
        if docker_platform:
            client.images.pull(dockerhub_image_uri, platform=docker_platform)
        else:
            client.images.pull(dockerhub_image_uri)

        abs_workspace_dir = os.path.abspath(workspace_dir)
        volumes = {abs_workspace_dir: {"bind": "/workspace", "mode": "rw"}}
        run_kwargs = {
            "volumes": volumes, "detach": True, "remove": True,
            "entrypoint": "/bin/bash", "command": ["-c", "bash /workspace/entryscript.sh"],
        }
        if block_network:
            run_kwargs["network_mode"] = "none"
        if docker_platform:
            run_kwargs["platform"] = docker_platform

        container = client.containers.run(dockerhub_image_uri, **run_kwargs)
        result = container.wait()
        status_code = result.get("StatusCode", 1) if isinstance(result, dict) else 1
        if status_code != 0:
            print(f"Entryscript failed for {uid} with return code: {status_code}")

        output = collect_outputs_local(workspace_dir, uid_dir, uid, prefix)
        if output is None:
            return None
        save_entryscript_copy(uid_dir, prefix, entryscript_content)
        return output
    except Exception as e:
        raise


def parse_args():
    parser = argparse.ArgumentParser(description="Run SWE-bench Pro evaluations")
    parser.add_argument("--raw_sample_path", required=True)
    parser.add_argument("--patch_path", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--dockerhub_username", required=True)
    parser.add_argument("--dockerhub_repo", required=True)
    parser.add_argument("--scripts_dir", required=True)
    parser.add_argument("--use_local_docker", action="store_true")
    parser.add_argument("--docker_platform", default=None)
    parser.add_argument("--redo", action="store_true")
    parser.add_argument("--num_workers", type=int, default=50)
    parser.add_argument("--block_network", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.raw_sample_path.endswith(".jsonl"):
        raw_sample_df = pd.read_json(args.raw_sample_path, lines=True)
    else:
        raw_sample_df = pd.read_csv(args.raw_sample_path)

    raw_sample_df = raw_sample_df.fillna("")
    raw_sample_df = raw_sample_df.set_index("instance_id", drop=False)
    
    # Load instances.yaml to get image_name field if it exists
    instances_yaml_path = os.path.join(os.path.dirname(args.raw_sample_path), "instances.yaml")
    if os.path.exists(instances_yaml_path):
        try:
            import yaml
            with open(instances_yaml_path, "r") as f:
                instances = yaml.safe_load(f)
            # Create a mapping of instance_id to image_name
            image_name_map = {inst["instance_id"]: inst.get("image_name", "") for inst in instances if isinstance(inst, dict)}
            # Add image_name column to dataframe
            raw_sample_df["image_name"] = raw_sample_df["instance_id"].map(image_name_map).fillna("")
        except Exception as e:
            print(f"Warning: Could not load image names from instances.yaml: {e}")

    with open(args.patch_path, "r") as f:
        patches_to_run = json.load(f)
    eval_results = {}

    valid_patches = []
    missing_instances = []
    for patch_sample in patches_to_run:
        instance_id = patch_sample["instance_id"]
        if instance_id in raw_sample_df.index:
            valid_patches.append(patch_sample)
        else:
            missing_instances.append(instance_id)

    if missing_instances:
        print(f"Warning: {len(missing_instances)} patch instances not in raw sample data")

    detected_platform = None
    if args.use_local_docker and args.docker_platform is None:
        try:
            if py_platform.machine().lower() in {"arm64", "aarch64"}:
                detected_platform = "linux/amd64"
        except Exception:
            pass

    eval_fn = eval_with_docker if args.use_local_docker else eval_with_modal

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.num_workers) as executor:
        future_to_patch = {
            executor.submit(
                eval_fn,
                patch_sample.get("model_patch", patch_sample.get("patch", "")),
                raw_sample_df.loc[patch_sample["instance_id"]],
                args.output_dir, args.dockerhub_username, args.scripts_dir, args.dockerhub_repo,
                prefix=patch_sample.get("prefix", ""), redo=args.redo,
                block_network=args.block_network,
                docker_platform=(args.docker_platform or detected_platform) if args.use_local_docker else None,
                attempt=patch_sample.get("attempt"),
            ): patch_sample
            for patch_sample in valid_patches
        }

        pbar = tqdm(concurrent.futures.as_completed(future_to_patch), total=len(valid_patches), desc="Evals", unit="eval")
        for future in pbar:
            patch_sample = future_to_patch[future]
            instance_id = patch_sample["instance_id"]
            attempt = patch_sample.get("attempt")
            result_key = f"{instance_id}:attempt_{attempt}" if attempt else instance_id
            output = future.result()
            if output is None:
                eval_results[result_key] = False
                status = "fail"
            else:
                if instance_id not in raw_sample_df.index:
                    eval_results[result_key] = False
                    status = "fail"
                else:
                    raw_sample = raw_sample_df.loc[instance_id]
                    passed_tests = {x["name"] for x in output["tests"] if x["status"] == "PASSED"}
                    f2p = set(eval(raw_sample["fail_to_pass"]))
                    p2p = set(eval(raw_sample["pass_to_pass"]))
                    result = (f2p | p2p) <= passed_tests
                    eval_results[result_key] = result
                    status = "pass" if result else "fail"

                    if attempt is not None:
                        task_results_dir = os.path.join(
                            args.output_dir, instance_id, f"attempt_{attempt}", "eval_results"
                        )
                        os.makedirs(task_results_dir, exist_ok=True)
                        with open(os.path.join(task_results_dir, "eval_results.json"), "w") as f:
                            json.dump({instance_id: result}, f)

            passed = sum(eval_results.values())
            total = len(eval_results)
            task_label = f"{instance_id}:{attempt}" if attempt else instance_id
            pbar.set_postfix_str(f"{passed}/{total} passed, {task_label} {status}")

    with open(os.path.join(args.output_dir, "eval_results.json"), "w") as f:
        json.dump(eval_results, f)
    print("Overall accuracy:", sum(eval_results.values()) / len(eval_results))


if __name__ == "__main__":
    main()
