import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from checkin import CheckIn
from utils.config import AccountConfig, ProviderConfig


def make_checkin(extra=None):
    extra = extra or {}
    account = AccountConfig.from_dict({"provider": "abrdns_checkin", **extra})
    provider = ProviderConfig(
        name="abrdns_checkin",
        origin="https://checkin.new-api.abrdns.com",
        check_in_path=None,
        topup_path=None,
    )
    return CheckIn("abrdns", account, provider)


def test_custom_flow_name_normalizes_blank_default():
    checkin = make_checkin()

    assert checkin.get_custom_flow_name() == ""


def test_custom_flow_user_info_matches_main_summary_shape():
    checkin = make_checkin()

    user_info = checkin.build_custom_flow_user_info("done")

    assert user_info == {
        "success": True,
        "quota": 0,
        "used_quota": 0,
        "bonus_quota": 0,
        "display": "done",
    }


def test_resolve_abrdns_response_success_message():
    checkin = make_checkin()

    result = checkin.resolve_abrdns_checkin_response(
        {"status": 200, "payload": {"success": True, "message": "签到成功"}, "text": ""}
    )

    assert result["success"] is True
    assert result["status_code"] == 200


def test_resolve_abrdns_response_already_checked_in():
    checkin = make_checkin()

    result = checkin.resolve_abrdns_checkin_response(
        {"status": 400, "payload": {"success": False, "detail": "已经签到"}, "text": ""}
    )

    assert result["success"] is True


def test_resolve_abrdns_response_html_already_checked_in_is_cleaned():
    checkin = make_checkin()

    result = checkin.resolve_abrdns_checkin_response(
        {
            "status": 200,
            "payload": None,
            "text": "<!DOCTYPE html><html><body><style>.success{}</style><main>今日已签到 获得 $2.02</main></body></html>",
        }
    )

    assert result["success"] is True
    assert result["message"] == "今日已签到 获得 $2.02"


def test_resolve_abrdns_response_unauthorized_requires_login():
    checkin = make_checkin()

    result = checkin.resolve_abrdns_checkin_response(
        {"status": 401, "payload": {"detail": "请先登录"}, "text": ""}
    )

    assert result["success"] is False
    assert result["requires_login"] is True
