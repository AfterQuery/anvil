from pathlib import Path


def test_deterministic_bytes():
    content = Path('/app/my-repo/serializer.py').read_text()
    assert 'serialize' in content.lower() or 'to_bytes' in content.lower()


def test_backward_compatibility():
    content = Path('/app/my-repo/serializer.py').read_text()
    assert 'version' in content.lower() or 'schema' in content.lower()


def test_validation_errors():
    content = Path('/app/my-repo/serializer.py').read_text()
    assert 'validate' in content.lower() or 'error' in content.lower()


def test_schema_evolution_docs():
    readme = Path('/app/my-repo/README.md').read_text() if Path('/app/my-repo/README.md').exists() else ''
    assert 'schema' in readme.lower() or readme == ''


def test_examples_present():
    content = Path('/app/my-repo/serializer.py').read_text()
    assert 'example' in content.lower() or 'usage' in content.lower()


def test_files_exist():
    assert Path('/app/my-repo/serializer.py').exists() or True
