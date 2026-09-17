from datetime import datetime, timezone

import httpx
import pytest

from app.services import news

FEED = b'''<rss><channel><item><title>Player update</title><link>https://example.com/story</link><pubDate>Thu, 17 Sep 2026 10:00:00 GMT</pubDate></item><item><title>Unsafe</title><link>javascript:alert(1)</link><pubDate>Thu, 17 Sep 2026 10:00:00 GMT</pubDate></item></channel></rss>'''


def test_feed_parsing():
    articles = news.parse_feed(FEED, 'Test')
    assert len(articles) == 1
    assert articles[0]['published_at'] == '2026-09-17T10:00:00+00:00'
    with pytest.raises(ValueError):
        news.parse_feed(b'<!DOCTYPE rss><rss/>', 'Test')
    with pytest.raises(ValueError):
        news.parse_feed(b'x' * (news.MAX_BYTES + 1), 'Test')


def test_daily_persistence_and_failure(tmp_path, monkeypatch):
    monkeypatch.setenv('NEWS_CACHE_DIR', str(tmp_path))
    monkeypatch.setattr(news, '_last_attempt', None)
    monkeypatch.setattr(news, 'now', lambda: datetime(2026, 9, 17, 12, tzinfo=timezone.utc))
    calls = []
    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, content=FEED)
    client_type = httpx.Client
    client = client_type(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(news.httpx, 'Client', lambda **kwargs: client)
    first = news.get_news()
    assert len(first['articles']) == 1  # Identical links across sources collapse.
    assert first['stale'] is False
    assert news.read_snapshot()['articles'] == first['articles']
    assert news.get_news() == first
    assert len(calls) == 2
    monkeypatch.setattr(news, 'now', lambda: datetime(2026, 9, 18, 12, tzinfo=timezone.utc))
    def unavailable(request):
        raise httpx.ConnectError('offline')
    failed_client = client_type(transport=httpx.MockTransport(unavailable))
    monkeypatch.setattr(news.httpx, 'Client', lambda **kwargs: failed_client)
    fallback = news.get_news()
    assert fallback['stale'] is True
    assert fallback['articles'] == first['articles']
    assert len(fallback['warnings']) == 2
