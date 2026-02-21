import json
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
    combined = stdout + "\n" + stderr

    # Pattern for pytest verbose output: path::test_name STATUS
    # Example: task_tests.py::test_empty_log_file PASSED
    pytest_pattern = re.compile(
        r'^([\w/.-]+\.py::(?:[\w]+::)?[\w]+)\s+(PASSED|FAILED|SKIPPED|ERROR|XFAIL)',
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
        simple_pattern = re.compile(r'(test_\w+).*?(PASSED|FAILED|SKIPPED|ERROR)', re.IGNORECASE)
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
