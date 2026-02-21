Submission checklist for advanced-dataset

Status: VERIFIED (local tests and smoke-tests completed)

Files produced:
- `advanced-dataset-submission.tgz` (archive of `advanced-dataset`)

Checks performed:
- Ran pre-patch tests (NOP) — confirmed failing baseline.
- Verified `gold_patches.json` and applied patches into `my-repo`.
- Fixed `my-repo/cache.py` and `my-repo/app.py` where necessary.
- Consolidated `my-repo/README.md` to include required hints.
- Ran `python -m compileall` to ensure no syntax errors.
- Ran full pytest per-task: all tasks passed (10 tasks × 6 tests each).
- Built local Docker image from `datasets/advanced-dataset/Dockerfile` successfully.
- Performed container smoke-test by mounting `my-repo` into `python:3.12-slim` and starting `app.py`.
  - HTTP endpoint returned `200` on `http://localhost:8000/`.

How to reproduce locally

1. Extract archive:

```bash
cd /tmp
tar -xzf advanced-dataset-submission.tgz
cd advanced-dataset
```

2. Run local tests:

```bash
python -m pytest task-*/task_tests.py -q
```

3. Build the included Docker image (optional, image in repo's Dockerfile is minimal):

```bash
cd datasets/advanced-dataset
docker build -t anvil-advanced-dataset:local .
```

4. Run the app (mount-based smoke test):

```bash
docker run -d --rm -p 8000:8000 -v $(pwd)/my-repo:/app python:3.12-slim sh -c "cd /app && pip install flask >/tmp/pip.log 2>&1 || true; python app.py"
curl http://localhost:8000/
```

Notes & recommendations before official submission

- If you plan to publish the Docker image to a registry, ensure you have CI to build and push the image securely.
- Consider adding `requirements.txt` or `pyproject.toml` per-task where complex dependencies exist.
- Confirm `gold_patches.json` contents are final and represent intended oracle solutions (currently contains minimal working implementations for tasks 2–10).
- Optionally run the official oracle validation agent on the platform (requires image publishing and the platform's validation steps).

Signed-off-by: Automated verification agent
