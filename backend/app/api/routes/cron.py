import hmac
import os

from fastapi import APIRouter, Header, HTTPException
from app.providers.weekly_cache import data_dir, save_snapshot
from app.services.news import get_news
from app.services.report_collector import refresh_current_reports

router = APIRouter(tags=['scheduled updates'])


@router.get('/cron/refresh')
def refresh(authorization: str | None = Header(default=None)):
    secret = os.getenv('CRON_SECRET')
    if not secret or not hmac.compare_digest(authorization or '', f'Bearer {secret}'):
        raise HTTPException(status_code=401, detail='Unauthorized')
    news = get_news()
    reports = refresh_current_reports()
    if reports and reports.verified:
        try:
            save_snapshot(reports, data_dir())
        except OSError as exc:
            raise HTTPException(status_code=503, detail='Report storage unavailable') from exc
    if news['stale'] or any('persistent storage' in warning for warning in news['warnings']) or (reports and not reports.verified):
        raise HTTPException(status_code=503, detail='One or more providers could not be refreshed; saved data retained')
    return {'ok': True, 'headlines': len(news['articles']), 'news_fetched_at': news['fetched_at'],
            'report_week': reports.week if reports else None}
