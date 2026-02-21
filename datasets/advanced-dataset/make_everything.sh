#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "Installing test requirements..."
python -m pip install -r requirements.txt >/dev/null

RESULTS_FILE="runs_summary.json"
echo "{" > "$RESULTS_FILE"

first=true
for i in $(seq 1 10); do
  TASK_DIR="task-$i"
  echo "--- Running tests for $TASK_DIR ---"
  pushd "$TASK_DIR" >/dev/null
  # Run tests; capture pytest -q output
  if pytest -q --maxfail=1 > pytest_output.txt 2>&1; then
    status="passed"
  else
    status="failed"
  fi
  # Parse output using parser if present
  if [ -x parser.py ] || [ -f parser.py ]; then
    python parser.py < pytest_output.txt > parser_result.json || echo '{}' > parser_result.json
  else
    echo '{"raw": "no parser", "passed": 0, "failed": 0}' > parser_result.json
  fi
  # Append to results
  if [ "$first" = true ]; then
    first=false
  else
    echo "," >> "$RESULTS_FILE"
  fi
  echo "\"task-$i\": {\"status\": \"$status\", \"parser\": "$(cat parser_result.json | sed 's/"/\\"/g')" }" >> "$RESULTS_FILE"
  popd >/dev/null
done

echo "}" >> "$RESULTS_FILE"

echo "Generating instances.yaml and gold_patches.json stubs..."
INSTANCES_FILE="instances.yaml"
GOLD_FILE="gold_patches.json"

printf "instances:\n" > "$INSTANCES_FILE"
for i in $(seq 1 10); do
  instance_id="advanced-dataset.task-$i"
  printf "  - instance_id: %s\n    test_files: task-%d/task_tests.py\n" "$instance_id" "$i" >> "$INSTANCES_FILE"
done

printf "{\n  \"gold_patches\": [\n" > "$GOLD_FILE"
for i in $(seq 1 10); do
  if [ $i -gt 1 ]; then
    printf ",\n" >> "$GOLD_FILE"
  fi
  printf "    {\"instance_id\": \"advanced-dataset.task-%d\", \"patch\": null}" "$i" >> "$GOLD_FILE"
done
printf "\n  ]\n}\n" >> "$GOLD_FILE"

echo "Creating zip bundle advanced-dataset.zip..."
zip -r advanced-dataset.zip . >/dev/null

echo "Done. Summary: $RESULTS_FILE, $INSTANCES_FILE, $GOLD_FILE, advanced-dataset.zip"
