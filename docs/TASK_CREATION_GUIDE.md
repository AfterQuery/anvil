# Task Creation Guide

This guide explains how to create evaluation tasks for Anvil.

--

## Generated Structure

The wizard creates the following structure:

```
my-dataset/
├── Dockerfile                    # Base environment
├── requirements.txt              # pytest dependencies
├── my-repo/                      # Your repository
├── task-1/
│   ├── Dockerfile               # FROM {user}/sweap-images:{dataset}.base
│   ├── instance_info.txt        # Instance ID, FAIL_TO_PASS, PASS_TO_PASS
│   ├── run_script.sh            # Bash script with embedded tests
│   ├── task_tests.py            # Your pytest tests
│   ├── parser.py                # Parses pytest output to JSON
│   └── tasks.csv                # Full task specification
├── task-2/
└── ...
```

---

## Step-by-Step Guide

### Prerequisites

```bash
# Install anvil
uv sync

# Set up Docker Hub credentials (for publishing)
export REGISTRY_USERNAME=your-dockerhub-username
export REGISTRY_PASSWORD=your-dockerhub-password

# Or add to .env file
echo "REGISTRY_USERNAME=your-dockerhub-username" >> .env
echo "REGISTRY_PASSWORD=your-dockerhub-password" >> .env
```

### Step 1: Initialize Dataset

```bash
anvil init-dataset \
  --dataset my-dataset \
  --repo-path /path/to/your/repo \
  --base-image golang:1.22
```

| Option | Description |
|--------|-------------|
| `--dataset, -d` | Dataset name (alphanumeric + hyphens) |
| `--repo-path` | Path to your git repository |
| `--base-image` | Docker base image (`golang:1.22`, `python:3.12`, `node:20`, etc.) |

### Step 2: Create Your Task Files

**problem.md** - Describe what needs to be implemented:

```markdown
## Task: Add User Profile Endpoint

Implement a GET /api/profile endpoint that returns the authenticated user's profile.

Requirements:
1. Add GetProfile method to UserService interface
2. Implement the method in the service
3. Add controller handler
4. Register the route with authentication middleware

The endpoint should return 401 if not authenticated, 404 if user not found.
```

**tests.py** - Pytest tests that verify the implementation:

```python
from pathlib import Path

def test_get_profile_in_interface():
    """Test that GetProfile is defined in the interface."""
    content = Path("/app/my-repo/internal/service/user.go").read_text()
    assert "GetProfile" in content, "GetProfile not in interface"

def test_get_profile_implemented():
    """Test that GetProfile is implemented."""
    content = Path("/app/my-repo/internal/service/user.go").read_text()
    assert "func (s *userService) GetProfile" in content

def test_profile_route_exists():
    """Test that /profile route is registered."""
    content = Path("/app/my-repo/routes/routes.go").read_text()
    assert "/profile" in content and "GetProfile" in content
```

### Step 3: Add Task with --capture-diff

```bash
anvil add-task -d my-dataset \
  --problem-file problem.md \
  --tests-file tests.py \
  --capture-diff
```

**What happens:**

```
=== Capture Diff Mode ===
Repository: /path/to/my-dataset/my-repo
Base commit: abc123def456

Make your changes to the repository now.
Edit files in: /path/to/my-dataset/my-repo

Type 'done' when done making changes...
```

1. **You edit the repo** - Make the changes that solve the task
2. **Press Enter** - When you're done editing
3. **Diff is captured** - The wizard runs `git diff` and shows a preview
4. **Confirm** - "Use this diff?"
5. **Repo resets** - "Reset repo for next task?" - repo returns to clean state

### Step 4: Repeat for More Tasks

```bash
# Task 2
anvil add-task -d my-dataset \
  --problem-file task2/problem.md \
  --tests-file task2/tests.py \
  --capture-diff

# Task 3
anvil add-task -d my-dataset \
  --problem-file task3/problem.md \
  --tests-file task3/tests.py \
  --capture-diff
```

Each time the repo starts clean (from the reset) so you can make fresh changes.

### Step 5: Validate

```bash
anvil validate-dataset -d my-dataset
```

### Step 6: Convert to Anvil Format

```bash
anvil convert-dataset -d my-dataset -u your-username --dockerhub-repo sweap-images
```

This generates `instances.yaml`, `gold_patches.json`, and the directory structure needed for evaluation.

### Step 7: Publish Docker Images

```bash
anvil publish-images -d my-dataset -u your-username --repo sweap-images
```

### Step 8: Verify with Oracle Agent

After publishing images, verify your tasks using the **oracle** agent:

```bash
# Oracle agent: applies gold patches, all tests should PASS
anvil run-evals -d my-dataset --agent oracle -u your-username --dockerhub-repo sweap-images
```

The oracle agent applies your gold patches and runs the tests. All tests should pass if your solution is correct.

**Prerequisites:**
- Modal account configured (`modal setup`)
- Docker Hub credentials in `.env` or environment
- Images published to Docker Hub (step 7)

If tests fail unexpectedly:
- **oracle fails**: Your gold patch doesn't satisfy the tests, or patch doesn't apply cleanly

### Step 9: Run with an Agent

```bash
anvil run-evals -d my-dataset \
  --agent mini-swe-agent \
  --model anthropic/claude-sonnet-4-20250514 \
  -u your-username \
  --dockerhub-repo sweap-images
```

---

## Writing Good Tests

### Structural Tests (Recommended)

Check for code patterns without executing:

```python
from pathlib import Path

def test_method_exists():
    content = Path("/app/my-repo/service.go").read_text()
    assert "func (s *Service) GetProfile" in content

def test_route_protected():
    content = Path("/app/my-repo/routes.go").read_text()
    assert "AuthMiddleware" in content
    assert "/profile" in content
```

**Why structural tests?**
- Fast (no compilation)
- Language-agnostic
- Predictable results
- Easy to debug

### Tips for Test Paths

Files are mounted at `/app/{repo-name}/`:

```python
# If your repo is "my-api", files are at:
Path("/app/my-api/internal/service/user.go")
Path("/app/my-api/routes/routes.go")
```

### Test Classification: FAIL_TO_PASS vs PASS_TO_PASS

Tests are classified into two categories:

| Category | Before Patch | After Patch | Purpose |
|----------|--------------|-------------|---------|
| **FAIL_TO_PASS** | FAIL | PASS | Tests the new functionality being added |
| **PASS_TO_PASS** | PASS | PASS | Regression tests (existing functionality) |

**FAIL_TO_PASS** (most common):
- Tests that verify the new feature or bug fix
- These tests FAIL on the original code and PASS after applying the patch
- If not specified, all detected tests are assumed to be FAIL_TO_PASS

```bash
# Explicitly specify which tests are FAIL_TO_PASS
anvil add-task -d my-dataset \
  --tests-file tests.py \
  --fail-to-pass "test_new_feature,test_edge_case"
```

**PASS_TO_PASS** (optional):
- Regression tests that ensure existing functionality isn't broken
- These tests PASS both before and after the patch
- Use when you want to verify the patch doesn't break existing behavior

```bash
# Include regression tests
anvil add-task -d my-dataset \
  --tests-file tests.py \
  --fail-to-pass "test_new_feature" \
  --pass-to-pass "test_existing_works,test_other_feature"
```

**When to use PASS_TO_PASS:**
- When your patch touches code that has existing functionality
- When you want to ensure backwards compatibility
- When testing a bug fix that shouldn't affect other features

---

## Alternative: Pre-made Patch Files

If you already have solution diffs, you can skip `--capture-diff`:

```bash
anvil add-task -d my-dataset \
  --problem-file problem.md \
  --patch-file solution.diff \
  --tests-file tests.py \
  --fail-to-pass "test_a,test_b,test_c"
```

To create a diff manually:

```bash
cd my-repo
# Make changes
git diff > ../solution.diff
# Reset
git checkout .
```

---

## Troubleshooting

### Oracle Fails

1. **Patch doesn't apply**
   ```bash
   cd my-dataset/my-repo
   git apply ../task-1/tasks.csv  # Extract patch and test
   ```

2. **Tests can't find files** - Check paths match `/app/{repo-name}/...`

3. **Test names mismatch** - Ensure `fail_to_pass` matches function names exactly

### Images Don't Build

1. Check Docker is running
2. Verify `REGISTRY_USERNAME` and `REGISTRY_PASSWORD`
3. Check Dockerfile syntax

---

## File Format Reference

### instance_info.txt

```
Instance ID: my-dataset.task-1
Test Files: tasks/task-1/task_tests.py
FAIL_TO_PASS: ['test_get_profile_in_interface', 'test_get_profile_implemented']
PASS_TO_PASS: []
```

### Task Dockerfile

```dockerfile
FROM afterquery/sweap-images:my-dataset.base
WORKDIR /app
```

### tasks.csv Columns

`repo`, `instance_id`, `base_commit`, `patch`, `test_patch`, `problem_statement`, `requirements`, `interface`, `repo_language`, `fail_to_pass`, `pass_to_pass`, `issue_specificity`, `issue_categories`, `before_repo_set_cmd`, `selected_test_files_to_run`

---

## Command Reference

| Command | Purpose |
|---------|---------|
| `anvil init-dataset -d NAME --repo-path PATH` | Create new dataset |
| `anvil add-task -d NAME --problem-file F --tests-file F -c` | Add task with diff capture |
| `anvil add-task -d NAME --problem-file F --patch-file F --tests-file F` | Add task with pre-made patch |
| `anvil validate-dataset -d NAME` | Check structure |
| `anvil convert-dataset -d NAME -u USER` | Generate Anvil files |
| `anvil publish-images -d NAME -u USER --repo REPO` | Build & push images |
| `anvil run-evals -d NAME --agent oracle -u USER --dockerhub-repo REPO` | Verify gold patches pass all tests |
| `anvil run-evals -d NAME --agent mini-swe-agent --model M -u USER --dockerhub-repo REPO` | Run evaluation with AI agent |
