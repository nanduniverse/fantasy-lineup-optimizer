"""Last-good public ESPN report snapshots, never treated as live on fallback."""
from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile

from app.services import cloud_storage


def data_dir() -> Path:
    default = Path(tempfile.gettempdir()) / 'fantasy-news' if os.getenv('VERCEL') else Path(__file__).resolve().parents[2] / '.data'
    return Path(os.getenv('NEWS_CACHE_DIR', str(default)))


def save_snapshot(snapshot, directory: Path):
    payload = asdict(snapshot)
    payload['playing_teams'] = sorted(snapshot.playing_teams)
    if cloud_storage.enabled():
        cloud_storage.write(f'weekly-{snapshot.season}-{snapshot.week}.json',
                            json.dumps(payload, default=lambda value: value.isoformat()).encode())
    directory.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=directory, delete=False) as output:
            temporary = output.name
            json.dump(payload, output, default=lambda value: value.isoformat())
        os.replace(temporary, directory / f'weekly-{snapshot.season}-{snapshot.week}.json')
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def load_snapshot(season: int, week: int, directory: Path):
    from app.providers.weekly import WeeklySnapshot, Report, DepthPlayer
    try:
        path = directory / f'weekly-{season}-{week}.json'
        content = None
        if cloud_storage.enabled():
            try:
                content = cloud_storage.read(path.name)
            except OSError:
                pass
        if content is None:
            if path.stat().st_size > 5_000_000:
                return None
            content = path.read_bytes()
        if len(content) > 5_000_000:
            return None
        data = json.loads(content)
        if (data['season'], data['week']) != (season, week):
            return None
        stamp = datetime.fromisoformat(data['fetched_at'])
        if stamp.tzinfo is None:
            return None
        return WeeklySnapshot(
            season=season, week=week, fetched_at=stamp, current_week=data['current_week'], verified=False,
            reports={pid: Report(row['status'], datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None)
                     for pid, row in data['reports'].items()},
            depths={team: tuple(DepthPlayer(**row) for row in rows) for team, rows in data['depths'].items()},
            playing_teams=frozenset(data['playing_teams']),
            warnings=(f'Saved ESPN reports from {stamp.isoformat()}. Reconnect to verify current availability.',),
            source_urls=tuple(data['source_urls']), saved=True,
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
