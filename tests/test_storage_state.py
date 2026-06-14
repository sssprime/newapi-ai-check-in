import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.storage_state import ensure_storage_state_from_env, merge_storage_states


def test_storage_state_uses_single_entry_as_fallback(tmp_path, monkeypatch):
    cache_path = tmp_path / "linuxdo.json"
    storage_state = {
        "cookies": [{"name": "_t", "value": "token", "domain": ".linux.do", "path": "/"}],
        "origins": [],
    }
    monkeypatch.setenv("STORATE_STATES_LINUXDO", json.dumps({"default": storage_state}))

    restored = ensure_storage_state_from_env(
        str(cache_path),
        "demo",
        "configured-username",
        env_name="STORATE_STATES_LINUXDO",
    )

    assert restored is True
    assert json.loads(cache_path.read_text(encoding="utf-8")) == storage_state


def test_merge_storage_states_keeps_site_and_linuxdo_cookies():
    site_state = {
        "cookies": [{"name": "session", "value": "site", "domain": "up.x666.me", "path": "/"}],
        "origins": [{"origin": "https://up.x666.me", "localStorage": [{"name": "userToken", "value": "jwt"}]}],
    }
    linuxdo_state = {
        "cookies": [{"name": "_t", "value": "linuxdo", "domain": ".linux.do", "path": "/"}],
        "origins": [],
    }

    merged = merge_storage_states(site_state, linuxdo_state)

    assert merged == {
        "cookies": [
            {"name": "session", "value": "site", "domain": "up.x666.me", "path": "/"},
            {"name": "_t", "value": "linuxdo", "domain": ".linux.do", "path": "/"},
        ],
        "origins": [{"origin": "https://up.x666.me", "localStorage": [{"name": "userToken", "value": "jwt"}]}],
    }


def test_merge_storage_states_later_cookie_wins():
    older_state = {
        "cookies": [{"name": "_t", "value": "old", "domain": ".linux.do", "path": "/"}],
        "origins": [],
    }
    newer_state = {
        "cookies": [{"name": "_t", "value": "new", "domain": ".linux.do", "path": "/"}],
        "origins": [],
    }

    merged = merge_storage_states(older_state, newer_state)

    assert merged == {
        "cookies": [{"name": "_t", "value": "new", "domain": ".linux.do", "path": "/"}],
        "origins": [],
    }
