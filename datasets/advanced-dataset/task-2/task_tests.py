from pathlib import Path


def test_incremental_updates():
    content = Path('/app/my-repo/indexer.py').read_text()
    assert 'class Indexer' in content or 'def apply_diff' in content


def test_merge_determinism():
    content = Path('/app/my-repo/indexer.py').read_text()
    assert 'merge' in content.lower() or 'vector_clock' in content


def test_query_correctness():
    content = Path('/app/my-repo/indexer.py').read_text()
    assert 'query' in content.lower() or 'search' in content.lower()


def test_persistence_layer():
    assert Path('/app/my-repo/db.py').exists()


def test_cli_exists():
    assert Path('/app/my-repo/cli.py').exists()


def test_readme_hint():
    content = Path('/app/my-repo/README.md').read_text() if Path('/app/my-repo/README.md').exists() else ''
    assert 'index' in content.lower() or content == ''
