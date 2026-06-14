#!/usr/bin/env python3
"""
storage state 相关工具
"""

import json
import os


def _resolve_storage_state_data(
    storage_states: dict,
    account_name: str,
    username: str,
    env_name: str,
) -> dict | None:
    storage_state_data = storage_states.get(username)
    if storage_state_data is None and len(storage_states) == 1:
        fallback_key, storage_state_data = next(iter(storage_states.items()))
        print(
            f"ℹ️ {account_name}: Storage state '{username}' was not found in {env_name}; "
            f"using the only available entry '{fallback_key}'"
        )

    if storage_state_data is None:
        print(f"⚠️ {account_name}: Skip restoring storage state because '{username}' was not found in {env_name}")
        return None

    if isinstance(storage_state_data, str):
        try:
            storage_state_data = json.loads(storage_state_data)
        except json.JSONDecodeError as exc:
            print(f"⚠️ {account_name}: Storage state '{username}' is not valid JSON: {exc}")
            return None

    if not isinstance(storage_state_data, dict):
        print(f"⚠️ {account_name}: Storage state '{username}' must be a JSON object")
        return None

    return storage_state_data


def load_storage_state_from_env(
    account_name: str,
    username: str,
    env_name: str = "STORATE_STATES",
) -> dict | None:
    """Load a Playwright storage state object from an environment variable."""
    storage_states_str = os.getenv(env_name, "")
    if not storage_states_str:
        print(f"⚠️ {account_name}: Skip loading storage state because {env_name} is empty or not set")
        return None

    try:
        storage_states = json.loads(storage_states_str)
    except json.JSONDecodeError as exc:
        print(f"⚠️ {account_name}: Failed to parse {env_name}: {exc}")
        return None

    if not isinstance(storage_states, dict):
        print(f"⚠️ {account_name}: {env_name} must be a JSON object")
        return None

    return _resolve_storage_state_data(storage_states, account_name, username, env_name)


def load_storage_state_file(cache_file_path: str) -> dict | None:
    """Load a Playwright storage state file if it exists and is valid."""
    if not cache_file_path or not os.path.exists(cache_file_path):
        return None

    try:
        with open(cache_file_path, encoding="utf-8") as file:
            storage_state_data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"⚠️ Failed to load storage state cache {cache_file_path}: {exc}")
        return None

    return storage_state_data if isinstance(storage_state_data, dict) else None


def merge_storage_states(*states: dict | None) -> dict | None:
    """Merge Playwright storage states, with later states overriding duplicate cookies/origins."""
    merged_cookies: dict[tuple[str, str, str], dict] = {}
    merged_origins: dict[str, dict] = {}
    has_state = False

    for state in states:
        if not isinstance(state, dict):
            continue
        has_state = True

        for cookie in state.get("cookies", []) or []:
            if not isinstance(cookie, dict):
                continue
            key = (cookie.get("domain", ""), cookie.get("path", ""), cookie.get("name", ""))
            merged_cookies[key] = cookie

        for origin in state.get("origins", []) or []:
            if not isinstance(origin, dict):
                continue
            origin_key = origin.get("origin")
            if origin_key:
                merged_origins[origin_key] = origin

    if not has_state:
        return None

    return {
        "cookies": list(merged_cookies.values()),
        "origins": list(merged_origins.values()),
    }


def ensure_storage_state_from_env(
    cache_file_path: str,
    account_name: str,
    username: str,
    env_name: str = "STORATE_STATES",
) -> bool:
    """当本地缓存不存在时，从环境变量恢复 storage state 文件。"""
    if not cache_file_path:
        print(f"⚠️ {account_name}: Skip restoring storage state because cache_file_path is empty")
        return False

    if os.path.exists(cache_file_path):
        print(f"⚠️ {account_name}: Skip restoring storage state because cache file already exists: {cache_file_path}")
        return False

    storage_states_str = os.getenv(env_name, "")
    if not storage_states_str:
        print(f"⚠️ {account_name}: Skip restoring storage state because {env_name} is empty or not set")
        return False

    try:
        storage_states = json.loads(storage_states_str)
    except json.JSONDecodeError as exc:
        print(f"⚠️ {account_name}: Failed to parse {env_name}: {exc}")
        return False

    if not isinstance(storage_states, dict):
        print(f"⚠️ {account_name}: {env_name} must be a JSON object")
        return False

    storage_state_data = _resolve_storage_state_data(storage_states, account_name, username, env_name)
    if storage_state_data is None:
        return False

    cache_dir = os.path.dirname(cache_file_path)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)

    with open(cache_file_path, "w", encoding="utf-8") as file:
        json.dump(storage_state_data, file, ensure_ascii=False, indent=2)

    print(f"ℹ️ {account_name}: Restored storage state from {env_name} -> {username}")
    return True
