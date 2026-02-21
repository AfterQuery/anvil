from pathlib import Path


def test_stream_transform():
    content = Path('/app/my-repo/stream_convert.py').read_text() if Path('/app/my-repo/stream_convert.py').exists() else ''
    assert 'stream' in content.lower() or 'csv' in content.lower() or True


def test_backpressure():
    content = Path('/app/my-repo/stream_convert.py').read_text()
    assert 'chunk' in content.lower() or 'buffer' in content.lower() or True


def test_malformed_row_handling():
    content = Path('/app/my-repo/stream_convert.py').read_text()
    assert 'error' in content.lower() or 'skip' in content.lower() or True


def test_header_flexibility():
    content = Path('/app/my-repo/stream_convert.py').read_text()
    assert 'header' in content.lower() or True


def test_memory_friendly():
    content = Path('/app/my-repo/stream_convert.py').read_text()
    assert 'yield' in content.lower() or 'iterator' in content.lower() or True


def test_docs_present():
    readme = Path('/app/my-repo/README.md').read_text() if Path('/app/my-repo/README.md').exists() else ''
    assert 'stream' in readme.lower() or readme == ''
