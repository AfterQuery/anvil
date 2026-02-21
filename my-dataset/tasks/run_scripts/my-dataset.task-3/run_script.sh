#!/usr/bin/env bash
set -euo pipefail

# Set ANVIL_APP_PATH to the repository directory if not already set
export ANVIL_APP_PATH="${ANVIL_APP_PATH:-./../my-repo}"

pytest -q --maxfail=1 task_tests.py

