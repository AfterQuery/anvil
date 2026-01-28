# Anvil

Run coding agent evaluations on SWE-bench style tasks using Modal sandboxes.

Anvil makes it easy to run agents against SWE-bench Pro tasks. It handles the infrastructure—spinning up Modal sandboxes, applying patches, running test harnesses, aggregating results—so you can benchmark different models and configurations in just 2 commands.

## Setup

**1. Install dependencies**
```bash
uv venv
source .venv/bin/activate
uv sync
```

**2. Configure environment**

Copy `.env.example` to `.env` and fill in:
- `OPENROUTER_API_KEY` (or whichever provider you're using)
- `REGISTRY_USERNAME` - your Docker Hub username
- `REGISTRY_PASSWORD` - a Docker Hub [access token](https://hub.docker.com/settings/security)

**3. Authenticate services**

Make sure Docker is running locally, then:
```bash
modal setup          # Modal account for sandboxed execution
docker login         # Docker Hub for image pulls
```

**4. Create a private Docker Hub repository**

Go to [hub.docker.com](https://hub.docker.com) and create a new **private** repository (e.g., `anvil-images`).

> ⚠️ Public repos will not work—Anvil refuses to push task images to public repositories to prevent data leakage.

## Usage

### Publish task images

Build and push Docker images for a dataset to your private repo:

```bash
anvil publish-images --dataset datasets/file-utilization -u <dockerhub-username> --repo anvil-images
```

Modal sandboxes pull images from Docker Hub, so task images need to be pushed there first.

To remove local anvil images: `docker rmi $(docker images <dockerhub-username>/anvil-images -q) --force`

### Run evaluations

Run an agent on all tasks and evaluate the patches:

```bash
anvil run-evals \
  --model openrouter/google/gemini-2.5-flash \
  --dataset datasets/file-utilization \
  --agent mini-swe-agent \
  --dockerhub-username <dockerhub-username> \
  --dockerhub-repo anvil-images \
  --n-attempts 3
```

Use `--n-attempts` to control how many runs per task (useful for pass@k metrics). Results are saved to `<dataset>/runs/<agent>_<model>/`. 

> 💡 **Progress is saved automatically** to minimize costs. If you re-run the same command, completed tasks are skipped—nothing runs on Modal for those tasks. Use `--no-continue` to start fresh.

### Oracle Agent

Use the `oracle` agent to validate your task harnesses before running LLM agents:

```bash
# Oracle: applies gold patches - all tests should PASS
anvil run-evals \
  --dataset datasets/my-dataset \
  --agent oracle \
  --dockerhub-username <username> \
  --dockerhub-repo anvil-images
```

The oracle agent skips LLM rollouts and applies gold patches from `gold_patches.json` directly. All tests should pass if your harness is correct.

**Prerequisites**: Requires Modal and Docker Hub setup (see [Setup](#setup)).

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | — | Model ID (required for agents, optional for oracle) |
| `--dataset` | — | Dataset ID or path |
| `--dockerhub-username` | — | Docker Hub username |
| `--dockerhub-repo` | — | Docker Hub repo name |
| `--agent` | mini-swe-agent | Agent to use (`mini-swe-agent` or `oracle`) |
| `--n-attempts` | 1 | Attempts per task (for pass@k) |
| `--max-parallel` | 30 | Concurrent agent runs |
| `--no-continue` | false | Start fresh, ignore previous results |
| `--max-wait` | auto | Minutes to wait for Modal rate limits |

## Creating Custom Tasks

Anvil includes a task creation wizard to help you build your own evaluation datasets.

### Quick Start

```bash
# 1. Initialize dataset with your repository
anvil init-dataset -d my-dataset --repo-path ./my-repo --base-image golang:1.22

# 2. Add tasks (problem statement + solution patch + tests)
anvil add-task -d my-dataset \
  --problem-file problem.md \
  --patch-file solution.diff \
  --tests-file tests.py \
  --fail-to-pass "test_feature_works,test_edge_case"

# 3. Convert to Anvil evaluation format
anvil convert-dataset -d my-dataset -u <dockerhub-username>

# 4. Publish and verify with oracle
anvil publish-images -d my-dataset -u <dockerhub-username> --repo anvil-images
anvil run-evals -d my-dataset --agent oracle -u <dockerhub-username> --dockerhub-repo anvil-images
```

See **[docs/TASK_CREATION_GUIDE.md](docs/TASK_CREATION_GUIDE.md)** for the complete guide including:
- Writing effective structural tests
- Task file format reference
- Troubleshooting tips
- Full workflow example

## How it works

1. **Agent phase**: Each task runs in a Modal sandbox using the pre-built Docker image. The agent (mini-swe-agent) receives the problem statement and generates a patch.

2. **Eval phase**: Patches are applied and test harnesses run inside containers. Results are aggregated into pass/fail per task.

3. **Output**: Trajectories, patches, stdout/stderr, and eval results are saved per-task. A summary with pass@k metrics is printed at the end.
