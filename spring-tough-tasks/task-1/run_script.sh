#!/bin/bash
set -e

cd /app

# Create test directory preserving original structure
mkdir -p tasks/task-1

cat > tasks/task-1/task_tests.py << 'ANVIL_TEST_CODE'
import pytest
import requests
import time

def test_rate_limiting():
    # URL for the API
    url = "http://localhost:8080/api/products"

    # Make 5 allowed requests
    for i in range(5):
        response = requests.get(url)
        assert response.status_code == 200, f"Request {i+1} failed"

    # The 6th request should be blocked (429 Too Many Requests)
    response = requests.get(url)
    assert response.status_code == 429, "Rate limiting did not work!"
ANVIL_TEST_CODE

python3 -m pytest -v tasks/task-1/task_tests.py 2>&1 || true
