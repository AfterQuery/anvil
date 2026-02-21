# Submission checklist and capture-diff guide

This guide explains how to implement tasks locally while preserving a clean
base commit so you can capture diffs for `anvil add-task --capture-diff` or
for generating `solution.diff` files for `gold_patches.json`.

Important: Do not use LLMs to write solution code if you intend to submit
these tasks to Project Anvil — all solution implementations must be your own.

Quick workflow (per task):

1. Start capture mode:

```bash
cd datasets/advanced-dataset
./capture_diff.sh start task-1
# edit files inside my-repo/ until the task is solved
```

2. Create the solution diff and reset:

```bash
./capture_diff.sh done task-1
# This writes task-1/solution.diff and resets the repo to the base commit
```

3. Add the task using the pre-made patch (or use `anvil add-task` with `--patch-file`):

```bash
anvil add-task -d advanced-dataset --problem-file task-1/problem.md \
  --patch-file task-1/solution.diff --tests-file task-1/task_tests.py \
  --fail-to-pass "test_concurrent_set_get,test_ttl_eviction,test_atomic_get_or_set"
```

Local validation and packaging:

```bash
# run the tests for the task you implemented
cd task-1
pytest -q

# run the helper that bundles dataset and generates stubs
cd ..
bash make_everything.sh
```

Checklist before submission:
- Ensure `task-N/problem.md` clearly describes requirements.
- Tests in `task-N/task_tests.py` are deterministic and structural when possible.
- `task-N/instance_info.txt` lists correct `FAIL_TO_PASS` tests.
- `task-N/solution.diff` applies cleanly with `git apply` to `my-repo` base.
- Run `anvil validate-dataset -d advanced-dataset` locally (if available).
- Confirm `anvil run-evals --agent oracle` passes once images are published.

If you want, I can:
- Help implement one task interactively (I will only provide guidance and tests).
- Generate `gold_patches.json` with placeholder metadata (no code).
- Package the dataset for upload.
