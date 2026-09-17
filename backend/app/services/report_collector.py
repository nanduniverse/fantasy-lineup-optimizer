"""Refresh public ESPN reports even when no browser is open."""
import asyncio
import logging

import httpx

from app.providers.weekly import weekly_provider
from app.services.current_season import SEASON


def refresh_current_reports():
    with httpx.Client(timeout=15) as client:
        board = weekly_provider._json(client, '/scoreboard?limit=1000')
    season = board.get('season', {})
    week = board.get('week', {}).get('number')
    if season.get('year') != SEASON or season.get('type') != 2 or not isinstance(week, int) or not 1 <= week <= 18:
        return  # Never assume this app's season is the current NFL season.
    snapshot = weekly_provider.snapshot(SEASON, week)
    if not snapshot.verified:
        logging.getLogger(__name__).warning('ESPN refresh unavailable: %s', snapshot.warnings)
    return snapshot


async def collect_reports():
    while True:
        try:
            await asyncio.to_thread(refresh_current_reports)
        except Exception:
            logging.getLogger(__name__).exception('Scheduled ESPN refresh failed')
        await asyncio.sleep(300)
