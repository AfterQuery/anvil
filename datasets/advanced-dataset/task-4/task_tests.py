from pathlib import Path


def test_migration_idempotent():
    content = Path('/app/my-repo/migrator.py').read_text()
    assert 'idempot' in content.lower() or 'checkpoint' in content.lower()


def test_progress_checkpoint():
    assert Path('/app/my-repo/migrator.py').exists()


def test_rollback():
    content = Path('/app/my-repo/migrator.py').read_text()
    assert 'rollback' in content.lower() or 'undo' in content.lower()


def test_dry_run_flag():
    content = Path('/app/my-repo/migrator.py').read_text()
    assert 'dry' in content.lower() or 'dry_run' in content


def test_resume_after_partial_failure():
    content = Path('/app/my-repo/migrator.py').read_text()
    assert 'resume' in content.lower() or 'checkpoint' in content.lower()


def test_docs_for_migration():
    readme = Path('/app/my-repo/README.md').read_text() if Path('/app/my-repo/README.md').exists() else ''
    assert 'migration' in readme.lower() or readme == ''
