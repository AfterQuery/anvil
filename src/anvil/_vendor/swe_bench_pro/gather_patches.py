#!/usr/bin/env python3
"""Gather .pred patch files and format them for swe_bench_pro_eval.py.

This file is adapted from the SWE-bench Pro OS repository:
https://github.com/scaleapi/SWE-bench_Pro-os
"""

import argparse
import json
from pathlib import Path


def find_pred_file(directory: Path, instance_id: str) -> Path | None:
    pred_files = list(directory.glob(f"{instance_id}*.pred"))
    if pred_files:
        return pred_files[0]
    pred_files = list(directory.glob("*.pred"))
    if pred_files:
        return pred_files[0]
    return None


def gather_patches_from_local(directory: str, prefix: str) -> list[dict[str, str]]:
    patches = []
    directory_path = Path(directory)

    if not directory_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    preds_json = directory_path / "preds.json"
    if preds_json.exists():
        print("Found preds.json, using it directly")
        try:
            with open(preds_json, "r") as f:
                data = json.load(f)
            for instance_id, entry in sorted(data.items()):
                patch_content = entry.get("model_patch") or entry.get("patch") or ""
                patches.append({
                    "instance_id": instance_id,
                    "patch": patch_content,
                    "prefix": prefix,
                })
            return patches
        except Exception as e:
            print(f"Warning: Failed to read preds.json ({e}), scanning directories")

    for item in sorted(directory_path.iterdir()):
        if not item.is_dir() or item.name in ("logs", "configs", "__pycache__"):
            continue

        pred_file = find_pred_file(item, item.name)
        if not pred_file:
            print(f"Warning: No .pred file found in {item.name}")
            continue

        try:
            with open(pred_file, "r") as f:
                content = f.read()

            instance_id = None
            patch_content = content

            try:
                pred_data = json.loads(content)
                if "instance_id" in pred_data:
                    instance_id = pred_data["instance_id"]
                if "model_patch" in pred_data:
                    patch_content = pred_data["model_patch"]
                elif "patch" in pred_data:
                    patch_content = pred_data["patch"]
            except json.JSONDecodeError:
                pass

            if not instance_id:
                instance_id = item.name

            patches.append({"instance_id": instance_id, "patch": patch_content, "prefix": prefix})
        except Exception as e:
            print(f"Error reading {pred_file}: {e}")

    return patches


def main():
    parser = argparse.ArgumentParser(description="Gather patches for swe_bench_pro_eval.py")
    parser.add_argument("--directory", type=str, required=True)
    parser.add_argument("--prefix", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    args = parser.parse_args()

    patches = gather_patches_from_local(args.directory, args.prefix)
    print(f"Found {len(patches)} patches, writing to {args.output}")

    with open(args.output, "w") as f:
        json.dump(patches, f, indent=2)


if __name__ == "__main__":
    main()
