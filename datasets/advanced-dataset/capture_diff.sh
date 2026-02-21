#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$ROOT_DIR/my-repo"

usage() {
  cat <<EOF
Usage: $0 <start|done> <task-dir>

start <task-dir>:
  - Initializes a git repo under my-repo and creates a base commit.
  - Example: ./capture_diff.sh start task-1

done <task-dir>:
  - Produces <task-dir>/solution.diff containing the changes since start
  - Resets the repo to the base commit so the workspace is clean.
  - Example: ./capture_diff.sh done task-1
EOF
}

if [ "$#" -ne 2 ]; then
  usage
  exit 1
fi

cmd="$1"
task_dir="$2"

if [ ! -d "$REPO_DIR" ]; then
  echo "Expected repository at $REPO_DIR"
  exit 1
fi

case "$cmd" in
  start)
    pushd "$REPO_DIR" >/dev/null
    if [ -d .git ]; then
      echo "Git repo already initialized under my-repo; skipping init."
    else
      git init -q
      git add -A
      git commit -m "base commit for capture" -q || true
      echo "Initialized git repo and created base commit. Edit files now." 
    fi
    popd >/dev/null
    ;;

  done)
    SOLUTION_PATH="$ROOT_DIR/$task_dir/solution.diff"
    if [ ! -d "$ROOT_DIR/$task_dir" ]; then
      echo "Task dir $ROOT_DIR/$task_dir does not exist"
      exit 1
    fi
    pushd "$REPO_DIR" >/dev/null
    if [ ! -d .git ]; then
      echo "No git repo found in my-repo. Run '$0 start $task_dir' first." >&2
      exit 1
    fi
    # Create diff against the committed base
    git add -A
    git diff --staged > "$SOLUTION_PATH" || true
    # If there were unstaged changes, include them too
    git diff >> "$SOLUTION_PATH" || true
    # Reset repo to base commit
    git reset --hard HEAD >/dev/null || true
    git clean -fd >/dev/null || true
    echo "Wrote solution diff to $SOLUTION_PATH and reset my-repo to base state."
    popd >/dev/null
    ;;

  *)
    usage
    exit 1
    ;;
esac
