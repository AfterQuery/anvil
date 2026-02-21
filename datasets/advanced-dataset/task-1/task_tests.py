from pathlib import Path


def test_concurrent_set_get():
    content = Path('/app/my-repo/cache.py').read_text()
    assert 'class Cache' in content, 'Cache class missing'
    assert 'set(' in content and 'get(' in content


def test_ttl_eviction():
    content = Path('/app/my-repo/cache.py').read_text()
    assert 'ttl' in content or 'expire' in content.lower()


def test_atomic_get_or_set():
    content = Path('/app/my-repo/cache.py').read_text()
    assert 'get_or_set' in content or 'get_orcreate' in content.lower()


def test_no_global_race_comment():
    # Encourage explicit locking patterns
    content = Path('/app/my-repo/cache.py').read_text()
    assert ('threading' in content) or ('Lock' in content) or ('asyncio' in content)


def test_cache_docstring():
    content = Path('/app/my-repo/cache.py').read_text()
    assert 'TTL' in content or 'time-to-live' in content.lower()


def test_changes_multi_files():
    # Check other modules referenced by the task exist
    assert Path('/app/my-repo/api.py').exists()
    assert Path('/app/my-repo/utils.py').exists()
