"""Bounded public RSS collection with an atomic, persistent last-good snapshot."""
import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import tempfile
from threading import Lock
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import httpx

from app.services import cloud_storage

SOURCES = {
    "RotoWire": "https://www.rotowire.com/rss/news.php?sport=NFL",
    "ESPN": "https://www.espn.com/espn/rss/nfl/news",
}
MAX_BYTES = 2_000_000
_lock = Lock()
_last_attempt = None


def cache_path():
    default = Path(tempfile.gettempdir()) / "fantasy-news" if os.getenv("VERCEL") else Path(__file__).resolve().parents[2] / ".data"
    return Path(os.getenv("NEWS_CACHE_DIR", str(default))) / "news.json"


def now():
    return datetime.now(timezone.utc)


def read_snapshot():
    try:
        content = None
        if cloud_storage.enabled():
            try:
                content = cloud_storage.read('news.json')
            except OSError:
                pass  # A last-good local snapshot can still be useful.
        data = json.loads(content if content is not None else cache_path().read_text())
        if not isinstance(data.get("articles"), list):
            raise ValueError("Invalid snapshot")
        return data
    except (OSError, ValueError, TypeError, AttributeError):
        return {"articles": [], "fetched_at": None, "warnings": []}


def parse_feed(content: bytes, source: str):
    if len(content) > MAX_BYTES or b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise ValueError("Unsupported feed")
    root = ET.fromstring(content)
    if root.tag not in {"rss", "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF"}:
        raise ValueError("Expected RSS")
    articles = []
    for item in root.findall(".//item")[:150]:
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        if not title or urlparse(url).scheme not in {"http", "https"} or not urlparse(url).hostname:
            continue
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "")
            published = published.replace(tzinfo=published.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()
        except (ValueError, TypeError, OverflowError):
            continue
        articles.append({"title": title[:500], "url": url, "source": source, "published_at": published})
    if not articles:
        raise ValueError("No dated articles in feed")
    return articles


def get_news():
    global _last_attempt
    with _lock:
        snapshot = read_snapshot()
        today = now().date().isoformat()
        if (snapshot.get("fetched_at") or "")[:10] != today and (_last_attempt is None or (now() - _last_attempt).total_seconds() >= 3600):
            _last_attempt = now()
            articles = {a["url"]: a for a in snapshot["articles"]}
            warnings = []
            succeeded = False
            with httpx.Client(timeout=15, follow_redirects=True, headers={"User-Agent": "FantasyLineupNews/1.0 (RSS reader)"}) as client:
                for source, url in SOURCES.items():
                    try:
                        with client.stream("GET", url) as response:
                            response.raise_for_status()
                            content = bytearray()
                            for chunk in response.iter_bytes():
                                content.extend(chunk)
                                if len(content) > MAX_BYTES:
                                    raise ValueError("Feed too large")
                        for article in parse_feed(bytes(content), source):
                            articles[article["url"]] = article
                        succeeded = True
                    except (httpx.HTTPError, ValueError, ET.ParseError):
                        warnings.append(f"{source} could not be refreshed; saved headlines retained.")
            snapshot = {
                "articles": sorted(articles.values(), key=lambda a: a["published_at"], reverse=True)[:100],
                "fetched_at": now().isoformat() if succeeded else snapshot.get("fetched_at"),
                "warnings": warnings,
            }
            try:
                if cloud_storage.enabled():
                    cloud_storage.write('news.json', json.dumps(snapshot).encode())
                path = cache_path()
                path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
                    json.dump(snapshot, output)
                    temporary = output.name
                os.replace(temporary, path)
            except OSError:
                snapshot["warnings"].append("News could not be saved to persistent storage.")
        snapshot["stale"] = (snapshot.get("fetched_at") or "")[:10] != today
        return snapshot


async def collect_daily():
    while True:
        try:
            await asyncio.to_thread(get_news)
        except Exception:
            # A collector failure must not shut down the application.
            import logging
            logging.getLogger(__name__).exception("News refresh failed")
        await asyncio.sleep(3600)


if __name__ == "__main__":
    print(json.dumps(get_news(), indent=2))
