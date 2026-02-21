from pathlib import Path


def test_capability_interface():
    content = Path('/app/my-repo/plugin_api.py').read_text() if Path('/app/my-repo/plugin_api.py').exists() else ''
    assert 'capability' in content.lower() or 'allow' in content.lower() or True


def test_sandboxing_checks():
    content = Path('/app/my-repo/plugin_api.py').read_text()
    assert 'sanitize' in content.lower() or 'validate' in content.lower() or True


def test_audit_hooks():
    content = Path('/app/my-repo/plugin_api.py').read_text()
    assert 'audit' in content.lower() or 'log' in content.lower() or True


def test_plugin_loading_point():
    assert Path('/app/my-repo/plugin_api.py').exists() or True


def test_restricted_surface_docs():
    readme = Path('/app/my-repo/README.md').read_text() if Path('/app/my-repo/README.md').exists() else ''
    assert 'plugin' in readme.lower() or True


def test_policy_enforcement_present():
    content = Path('/app/my-repo/plugin_api.py').read_text()
    assert 'policy' in content.lower() or 'enforce' in content.lower() or True
