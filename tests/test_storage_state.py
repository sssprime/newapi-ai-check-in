import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.storage_state import ensure_storage_state_from_env


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
