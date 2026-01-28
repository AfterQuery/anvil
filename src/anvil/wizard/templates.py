"""Static templates for task generation."""

# Parser script that converts pytest output to JSON
PARSER_PY = '''import json
import re
import sys
from pathlib import Path


def parse(stdout: str, stderr: str):
    """Parse pytest verbose output to extract test results.

    Handles formats:
    - pytest -v: 'test_file.py::test_name PASSED/FAILED/SKIPPED'
    - pytest -v with class: 'test_file.py::TestClass::test_name PASSED/FAILED'
    """
    tests = []
    combined = stdout + "\\n" + stderr

    # Pattern for pytest verbose output: path::test_name STATUS
    # Example: task_tests.py::test_empty_log_file PASSED
    pytest_pattern = re.compile(
        r'^([\\w/.-]+\\.py::(?:[\\w]+::)?[\\w]+)\\s+(PASSED|FAILED|SKIPPED|ERROR|XFAIL)',
        re.MULTILINE
    )

    for match in pytest_pattern.finditer(combined):
        full_name = match.group(1)
        status = match.group(2)
        # Extract just the test name (last component after ::)
        test_name = full_name.split("::")[-1]
        # Also try to get class::method format if present
        parts = full_name.split("::")
        if len(parts) == 3:
            # file::class::method -> class::method
            test_name = f"{parts[1]}::{parts[2]}"
        elif len(parts) == 2:
            # file::method -> method
            test_name = parts[1]
        tests.append({'name': test_name, 'status': status})

    # Fallback: simple pattern for older pytest or custom formats
    if not tests:
        simple_pattern = re.compile(r'(test_\\w+).*?(PASSED|FAILED|SKIPPED|ERROR)', re.IGNORECASE)
        for match in simple_pattern.finditer(combined):
            tests.append({'name': match.group(1), 'status': match.group(2).upper()})

    return {'tests': tests}


def main(stdout_path: str, stderr_path: str, output_path: str):
    s = Path(stdout_path).read_text() if stdout_path and Path(stdout_path).exists() else ''
    e = Path(stderr_path).read_text() if stderr_path and Path(stderr_path).exists() else ''
    data = parse(s, e)
    Path(output_path).write_text(json.dumps(data, indent=2))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
'''

# Base Dockerfile template
BASE_DOCKERFILE_TEMPLATE = '''FROM {base_image}

WORKDIR /app

RUN apt-get update && apt-get install -y \\
    build-essential cmake curl git tmux asciinema python3 python3-pip \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY . .
RUN chmod +x /app/run_tests.sh || true
'''

# Requirements for pytest
REQUIREMENTS_TXT = '''pytest>=7.0.0so 
pytest-timeout>=2.0.0
'''

# Task-specific Dockerfile (extends base image)
TASK_DOCKERFILE_TEMPLATE = '''FROM {dockerhub_username}/anvil-images:{dataset_id}.base
WORKDIR /app
'''

# Run script template that embeds tests via heredoc
RUN_SCRIPT_TEMPLATE = '''#!/bin/bash
set -e

cd /app

# Create test directory preserving original structure
mkdir -p tasks/{task_id}

cat > tasks/{task_id}/task_tests.py << 'EOF'
{test_code}
EOF

python3 -m pytest -v tasks/{task_id}/task_tests.py 2>&1 || true
'''

# Instance info template
INSTANCE_INFO_TEMPLATE = '''Instance ID: {instance_id}
Test Files: tasks/{task_id}/task_tests.py
FAIL_TO_PASS: {fail_to_pass}
PASS_TO_PASS: {pass_to_pass}
'''

# CSV header for tasks.csv
TASKS_CSV_HEADER = (
    "repo,instance_id,base_commit,patch,test_patch,problem_statement,"
    "requirements,interface,repo_language,fail_to_pass,pass_to_pass,"
    "issue_specificity,issue_categories,before_repo_set_cmd,selected_test_files_to_run"
)
