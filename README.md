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
anvil publish-images --dataset datasets/all-swe -u YOUR_USERNAME --repo anvil-images
```

Modal sandboxes pull images from Docker Hub, so task images need to be pushed there first.

### Run evaluations

Run an agent on all tasks and evaluate the patches:

```bash
anvil run-evals \
  --model openrouter/google/gemini-3-flash-preview \
  --dataset all-swe \
  --agent mini-swe-agent \
  --dockerhub-username YOUR_USERNAME \
  --dockerhub-repo anvil-images
```

Results go to `datasets/<dataset>/runs/<agent>_<model>/`. Re-running resumes from where it left off.

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--n-attempts` | 1 | Attempts per task (for pass@k) |
| `--max-parallel` | 30 | Concurrent agent runs |
| `--no-continue` | false | Start fresh, ignore previous results |
| `--max-wait` | auto | Minutes to wait for Modal rate limits |

## How it works

1. **Agent phase**: Each task runs in a Modal sandbox using the pre-built Docker image. The agent (mini-swe-agent) receives the problem statement and generates a patch.

2. **Eval phase**: Patches are applied and test harnesses run inside containers. Results are aggregated into pass/fail per task.

3. **Output**: Trajectories, patches, stdout/stderr, and eval results are saved per-task. A summary with pass@k metrics is printed at the end.
