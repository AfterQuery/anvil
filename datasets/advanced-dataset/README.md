# Advanced dataset scaffold

This dataset contains a synthetic `my-repo` and 10 challenging task folders
(`task-1` .. `task-10`).  Each task contains `problem.md`, `task_tests.py`, a
`run_script.sh`, a `parser.py`, `instance_info.txt`, and a `Dockerfile` that
references the dataset base image.

IMPORTANT: This scaffold intentionally omits solution code. You must implement
the solutions locally (or via the capture-diff flow) so they remain your own
original work.

To run tests locally (example):

```bash
python -m pip install -r requirements.txt
cd task-1
pytest -q
```
