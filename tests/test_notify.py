import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

# 添加项目根目录到 PATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(project_root / '.env')

from utils.notify import NotificationKit


@pytest.fixture
def notification_kit():
	return NotificationKit()


class FakeTelegramResponse:
	def __init__(self, status_code=200, payload=None, text=''):
		self.status_code = status_code
		self.payload = payload if payload is not None else {'ok': True}
		self.text = text

	def json(self):
		return self.payload


def test_send_telegram_splits_long_plain_text(monkeypatch, notification_kit):
	monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'token')
	monkeypatch.setenv('TELEGRAM_CHAT_ID', '123')
	calls = []

	def fake_post(url, json, timeout):
		calls.append({'url': url, 'json': json, 'timeout': timeout})
		return FakeTelegramResponse()

	monkeypatch.setattr('utils.notify.curl_requests.post', fake_post)

	notification_kit.send_telegram('Check-in Alert', 'line\n' + ('x' * 8000))

	assert len(calls) >= 2
	for call in calls:
		assert call['timeout'] == 30
		assert call['json']['chat_id'] == '123'
		assert 'parse_mode' not in call['json']
		assert len(call['json']['text']) <= 4096


def test_send_telegram_raises_on_api_error(monkeypatch, notification_kit):
	monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'token')
	monkeypatch.setenv('TELEGRAM_CHAT_ID', '123')

	def fake_post(url, json, timeout):
		return FakeTelegramResponse(
			status_code=400,
			payload={'ok': False, 'description': 'Bad Request: message is too long'},
			text='Bad Request: message is too long',
		)

	monkeypatch.setattr('utils.notify.curl_requests.post', fake_post)

	with pytest.raises(ValueError, match='Telegram API HTTP 400'):
		notification_kit.send_telegram('Check-in Alert', 'content')


def test_real_notification(notification_kit):
	"""真实接口测试，需要配置.env.local文件"""
	if os.getenv('ENABLE_REAL_TEST') != 'true':
		pytest.skip('未启用真实接口测试')

	notification_kit.push_message(
		'测试消息', f'这是一条测试消息\n发送时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
	)


@patch('smtplib.SMTP_SSL')
def test_send_email(mock_smtp, monkeypatch, notification_kit):
	monkeypatch.setenv('EMAIL_USER', 'bot@example.com')
	monkeypatch.setenv('EMAIL_PASS', 'password')
	monkeypatch.setenv('EMAIL_TO', 'user@example.com')
	mock_server = MagicMock()
	mock_smtp.return_value.__enter__.return_value = mock_server

	notification_kit.send_email('测试标题', '测试内容')

	assert mock_server.login.called
	assert mock_server.send_message.called


@patch('utils.notify.curl_requests.post')
def test_send_pushplus(mock_post, monkeypatch, notification_kit):
	monkeypatch.setenv('PUSHPLUS_TOKEN', 'test_token')

	notification_kit.send_pushplus('测试标题', '测试内容')

	mock_post.assert_called_once()
	args = mock_post.call_args[1]
	assert 'test_token' in str(args)


@patch('utils.notify.curl_requests.post')
def test_send_dingtalk(mock_post, monkeypatch, notification_kit):
	monkeypatch.setenv(
		'DINGDING_WEBHOOK',
		'https://oapi.dingtalk.com/robot/send?access_token=fbcd45f32f17dea5c762e82644c7f28945075e0b4d22953c8eebe064b106a96f',
	)

	notification_kit.send_dingtalk('测试标题', '测试内容')

	expected_webhook = 'https://oapi.dingtalk.com/robot/send?access_token=fbcd45f32f17dea5c762e82644c7f28945075e0b4d22953c8eebe064b106a96f'
	expected_data = {'msgtype': 'text', 'text': {'content': '测试标题\n测试内容'}}

	mock_post.assert_called_once_with(expected_webhook, json=expected_data, timeout=30)


@patch('utils.notify.curl_requests.post')
def test_send_feishu(mock_post, monkeypatch, notification_kit):
	monkeypatch.setenv('FEISHU_WEBHOOK', 'https://open.feishu.cn/webhook/test')

	notification_kit.send_feishu('测试标题', '测试内容')

	mock_post.assert_called_once()
	args = mock_post.call_args[1]
	assert 'card' in args['json']


@patch('utils.notify.curl_requests.post')
def test_send_wecom(mock_post, monkeypatch, notification_kit):
	monkeypatch.setenv('WEIXIN_WEBHOOK', 'http://weixin.example.com')

	notification_kit.send_wecom('测试标题', '测试内容')

	mock_post.assert_called_once_with(
		'http://weixin.example.com',
		json={'msgtype': 'text', 'text': {'content': '测试标题\n测试内容'}},
		timeout=30,
	)


def test_missing_config(monkeypatch):
	for key in (
		'EMAIL_USER',
		'EMAIL_PASS',
		'EMAIL_TO',
		'PUSHPLUS_TOKEN',
		'TELEGRAM_BOT_TOKEN',
		'TELEGRAM_CHAT_ID',
	):
		monkeypatch.delenv(key, raising=False)
	kit = NotificationKit()

	with pytest.raises(ValueError, match='Email configuration not set'):
		kit.send_email('测试', '测试')

	with pytest.raises(ValueError, match='PushPlus Token not configured'):
		kit.send_pushplus('测试', '测试')


def test_push_message(monkeypatch, notification_kit):
	called = []

	def record(name):
		def inner(self, *args, **kwargs):
			called.append(name)

		return inner

	for name in (
		'send_email',
		'send_pushplus',
		'send_serverPush',
		'send_dingtalk',
		'send_feishu',
		'send_wecom',
		'send_telegram',
	):
		monkeypatch.setattr(NotificationKit, name, record(name))

	notification_kit.push_message('测试标题', '测试内容')

	assert called == [
		'send_email',
		'send_pushplus',
		'send_serverPush',
		'send_dingtalk',
		'send_feishu',
		'send_wecom',
		'send_telegram',
	]
