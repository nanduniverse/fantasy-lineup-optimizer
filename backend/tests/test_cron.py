from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import cron


def test_cron_requires_configured_secret(monkeypatch):
    monkeypatch.delenv('CRON_SECRET', raising=False)
    client = TestClient(app)
    assert client.get('/api/cron/refresh').status_code == 401
    monkeypatch.setenv('CRON_SECRET', 'test-only-secret')
    assert client.get('/api/cron/refresh', headers={'Authorization': 'Bearer wrong'}).status_code == 401
    monkeypatch.setattr(cron, 'get_news', lambda: {'stale': False, 'articles': [], 'warnings': [], 'fetched_at': 'today'})
    monkeypatch.setattr(cron, 'refresh_current_reports', lambda: None)
    assert client.get('/api/cron/refresh', headers={'Authorization': 'Bearer test-only-secret'}).json()['ok']


def test_cron_reports_provider_failure(monkeypatch):
    monkeypatch.setenv('CRON_SECRET', 'test-only-secret')
    monkeypatch.setattr(cron, 'get_news', lambda: {'stale': True, 'articles': [], 'warnings': [], 'fetched_at': None})
    monkeypatch.setattr(cron, 'refresh_current_reports', lambda: None)
    assert TestClient(app).get('/api/cron/refresh', headers={'Authorization': 'Bearer test-only-secret'}).status_code == 503
