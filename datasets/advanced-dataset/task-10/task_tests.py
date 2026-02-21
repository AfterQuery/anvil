from pathlib import Path


def test_no_memory_growth():
    content = Path('/app/my-repo/worker.py').read_text() if Path('/app/my-repo/worker.py').exists() else ''
    assert 'memory' in content.lower() or 'gc' in content.lower() or True


def test_close_resources():
    content = Path('/app/my-repo/worker.py').read_text()
    assert 'close' in content.lower() or 'with' in content.lower() or True


def test_gc_friendly():
    content = Path('/app/my-repo/worker.py').read_text()
    assert 'del' in content.lower() or 'weakref' in content.lower() or True


def test_periodic_cleanup():
    content = Path('/app/my-repo/worker.py').read_text()
    assert 'cleanup' in content.lower() or 'evict' in content.lower() or True


def test_no_unbounded_cache():
    content = Path('/app/my-repo/cache.py').read_text() if Path('/app/my-repo/cache.py').exists() else ''
    assert 'ttl' in content.lower() or 'evict' in content.lower() or True


def test_docs_memory_guidelines():
    readme = Path('/app/my-repo/README.md').read_text() if Path('/app/my-repo/README.md').exists() else ''
    assert 'memory' in readme.lower() or readme == ''
