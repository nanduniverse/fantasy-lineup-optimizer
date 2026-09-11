"""Read-only ESPN league access. Authentication is request-scoped and never cached."""
import json
import httpx
from app.schemas.league import LeagueRequest
from app.providers.nflverse import ProviderError


def fetch_league(request: LeagueRequest, transport=None) -> dict:
    url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026/segments/0/leagues/{request.league_id}'
    cookies = {}
    if request.espn_s2:
        cookies['espn_s2'] = request.espn_s2.get_secret_value()
    if request.swid:
        cookies['SWID'] = request.swid.get_secret_value()
    try:
        with httpx.Client(timeout=20, transport=transport, cookies=cookies) as client:
            with client.stream('GET', url, params=[('view', v) for v in ('mTeam', 'mRoster', 'mSettings', 'mMatchup')]
                               + [('scoringPeriodId', str(request.week))]) as response:
                if response.status_code in (401, 403):
                    raise ProviderError('This ESPN league is private or access expired. Use the private-league fields to authorize access.')
                if response.status_code == 404:
                    raise ProviderError('League not found for 2026. Check the league ID and season.')
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 10 * 1024 * 1024:
                        raise ProviderError('League response exceeds the supported size.')
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ProviderError('ESPN returned an unsupported league response.')
        return data
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError('Could not read this ESPN league. Check access and try again.') from exc
