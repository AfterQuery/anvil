from pathlib import Path
import os

BASE = os.environ.get("ANVIL_APP_PATH", "/workspaces/anvil/my-dataset/my-repo")

def test_get_profile_in_interface():
    content = Path(f"{BASE}/service.py").read_text()
    assert "get_profile" in content, "get_profile not in interface"

def test_get_profile_implemented():
    content = Path(f"{BASE}/service.py").read_text()
    assert "def get_profile" in content or "def get_profile(self" in content

def test_profile_route_exists():
    content = Path(f"{BASE}/controller.py").read_text()
    assert "/api/profile" in content and "get_profile" in content
