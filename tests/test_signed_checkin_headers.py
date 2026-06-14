import base64
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from checkin import CheckIn
from utils.config import AccountConfig, ProviderConfig


class FakeResponse:
	def __init__(self, payload, status_code=200):
		self.payload = payload
		self.status_code = status_code
		self.headers = {"content-type": "application/json"}
		self.text = ""

	def json(self):
		return self.payload


class FakeSession:
	def __init__(self, payload):
		self.payload = payload
		self.requested_urls = []

	def get(self, url, headers=None, timeout=None):
		self.requested_urls.append(url)
		return FakeResponse(self.payload)


def make_checkin(extra=None):
	extra = extra or {}
	account = AccountConfig.from_dict(
		{
			"name": "signed",
			"provider": "signed",
			"api_user": "8947",
			"system_access_token": "token",
			**extra,
		}
	)
	provider = ProviderConfig(
		name="signed",
		origin="https://example.com",
		check_in_path="/api/user/checkin",
		check_in_status=True,
	)
	return CheckIn("signed", account, provider)


def test_huaibao_nonce_sha256_headers(monkeypatch):
	checkin = make_checkin({"check_in_header_mode": "huaibao_nonce_sha256"})
	session = FakeSession({"success": True, "data": {"checkin_nonce": "abc123"}})
	headers = {}

	monkeypatch.setattr("checkin.time.time", lambda: 1710000000)

	error = checkin.add_signed_check_in_headers(session, headers, "8947", "{}")

	assert error is None
	assert headers["X-Checkin-Timestamp"] == "1710000000"
	assert headers["X-Checkin-Signature"] == checkin.sha256_hex("8947:1710000000:abc123")
	assert session.requested_urls[0].startswith("https://example.com/api/user/checkin?month=")


def test_windhub_game_integrity_headers(monkeypatch):
	checkin = make_checkin({"check_in_header_mode": "windhub_game_integrity"})
	headers = {"User-Agent": "UnitTest", "Accept-Language": "en-US,en;q=0.9"}

	monkeypatch.setattr("checkin.time.time", lambda: 1710000000.123)
	monkeypatch.setattr("checkin.uuid.uuid4", lambda: "uuid-value")

	error = checkin.add_signed_check_in_headers(FakeSession({}), headers, "23823", "")

	assert error is None
	assert headers["X-Game-Action-Id"] == "uuid-value"
	assert headers["X-Game-Client-Ts"] == "1710000000123"
	assert headers["X-Game-Session-Id"] == "uuid-value"
	assert headers["X-Game-Client-Seq"] == "1"
	assert headers["X-Game-Body-SHA256"] == checkin.sha256_hex("")
	assert headers["X-Game-Client-Fingerprint"] == checkin.sha256_hex(
		"UnitTest|en-US|Win32|Asia/Shanghai|8|8"
	)


def test_windhub_check_in_uses_empty_body():
	checkin = make_checkin({"check_in_header_mode": "windhub_game_integrity"})

	assert checkin.get_check_in_request_body() is None


def test_windhub_pow_token(monkeypatch):
	checkin = make_checkin({"check_in_header_mode": "windhub_game_integrity"})
	session = FakeSession(
		{
			"success": True,
			"data": {
				"enabled": True,
				"challenge": "abc",
				"difficulty": 1,
				"path": "",
				"purpose": "",
				"body_hash": "",
			},
		}
	)

	monkeypatch.setattr("checkin.time.time", lambda: 1710000000.123)

	pow_token = checkin.get_windhub_pow_token(session, {})

	assert pow_token
	decoded = json.loads(base64.b64decode(pow_token).decode("utf-8"))
	assert decoded["challenge"] == "abc"
	assert decoded["pow"]["hash"].startswith("0")
	assert decoded["fingerprint"] == {"canvas": 1642478927, "webgl": 3627205444}
	assert decoded["behavior"] == {"score": 90, "moves": 24, "dist": 920}
	assert decoded["automation"] == []
	assert decoded["risk"] == 0
	assert decoded["ts"] == 1710000000123
