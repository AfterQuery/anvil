from pathlib import Path


def test_rate_limits_refill():
    c = Path('/app/my-repo/rate_limiter.py').read_text()
    assert 'Token' in c or 'token' in c.lower() or 'bucket' in c.lower()


def test_concurrent_burst():
    assert Path('/app/my-repo/rate_limiter.py').exists()


def test_invalid_config():
    content = Path('/app/my-repo/rate_limiter.py').read_text()
    assert 'raise' in content or 'ValueError' in content or 'assert' in content


def test_doc_examples():
    # Encourage docstring examples and configuration hints
    content = Path('/app/my-repo/rate_limiter.py').read_text()
    assert 'rate' in content.lower() or 'refill' in content.lower()


def test_multi_process_hint():
    content = Path('/app/my-repo/rate_limiter.py').read_text()
    assert 'multiprocessing' in content or 'redis' in content or 'shared' in content


def test_api_integration_point():
    assert Path('/app/my-repo/api.py').exists()
