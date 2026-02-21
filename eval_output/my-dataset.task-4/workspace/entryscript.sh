

cd /app
# If .git/ is missing (e.g. repo uploaded as zip without git history),
# initialize a git repo so git apply can work
if [ ! -d .git ]; then
    git init -q
    git add -A
    git commit -q -m "init" --allow-empty
fi
git reset --hard  2>/dev/null || true
git checkout  2>/dev/null || true
git apply -v --ignore-whitespace /workspace/patch.diff 2>&1 || \
patch -p1 --forward --reject-file=- --no-backup-if-mismatch < /workspace/patch.diff 2>&1 || true

# Ensure pip and pytest are available; install project requirements if present.
python3 -m pip install --upgrade pip setuptools wheel > /workspace/pip_install.log 2>&1 || true
if [ -f /app/requirements.txt ]; then
    python3 -m pip install -r /app/requirements.txt >> /workspace/pip_install.log 2>&1 || true
fi
python3 -m pip install pytest >> /workspace/pip_install.log 2>&1 || true

# Run tests and parse results
bash /workspace/run_script.sh task_tests.py > /workspace/stdout.log 2> /workspace/stderr.log
python3 /workspace/parser.py /workspace/stdout.log /workspace/stderr.log /workspace/output.json "['test_get_profile_in_interface', 'test_get_profile_implemented', 'test_profile_route_exists', 'test_get_profile_returns_dict', 'test_get_profile_contains_required_fields', 'test_get_profile_returns_none_for_missing_user']" "[]"
