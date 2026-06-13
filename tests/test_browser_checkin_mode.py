import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from checkin import CheckIn
from utils.config import AccountConfig, ProviderConfig


def make_checkin(extra=None):
	extra = extra or {}
	account = AccountConfig.from_dict({"provider": "demo", "api_user": "123", **extra})
	provider = ProviderConfig(
		name="demo",
		origin="https://example.com",
		check_in_path="/api/user/checkin",
	)
	return CheckIn("demo", account, provider)


def test_browser_checkin_disabled_by_default():
	checkin = make_checkin()

	assert not checkin.should_use_browser_check_in_first()
	assert not checkin.should_retry_browser_check_in({"error": "Turnstile token is empty"})


def test_auto_browser_mode_retries_failed_http_checkin():
	checkin = make_checkin({"check_in_mode": "auto_browser"})

	assert not checkin.should_use_browser_check_in_first()
	assert checkin.should_retry_browser_check_in({"error": "any failure"})


def test_browser_page_mode_runs_browser_first():
	checkin = make_checkin({"check_in_mode": "browser_page"})

	assert checkin.should_use_browser_check_in_first()
	assert checkin.should_retry_browser_check_in({"error": "any failure"})


def test_resolve_checkin_payload_success_and_already_checked():
	checkin = make_checkin()

	success = checkin.resolve_check_in_payload({"success": True, "data": {"quota_awarded": 500000}})
	already = checkin.resolve_check_in_payload({"success": False, "message": "\u5df2\u7ecf\u7b7e\u5230"})

	assert success["success"] is True
	assert success["data"]["quota_awarded"] == 500000
	assert already["success"] is True


def test_resolve_checkin_text_response_invalid_json_keeps_status():
	checkin = make_checkin()

	result = checkin.resolve_check_in_text_response(403, "<html>blocked</html>")

	assert result["success"] is False
	assert result["status_code"] == 403
	assert "Invalid response format" in result["error"]
