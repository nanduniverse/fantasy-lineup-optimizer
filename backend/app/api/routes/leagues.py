from fastapi import APIRouter, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from app.schemas.league import LeagueRequest, LeagueImport
from app.schemas.nfl import NflContext
from app.providers.leagues import fetch_league
from app.providers.nflverse import ProviderError
from app.services.league_import import parse_league
from app.api.routes.nfl import current_catalog_for

class PrivateInputRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def handler(request):
            try:
                return await original(request)
            except RequestValidationError as exc:
                # FastAPI normally echoes invalid inputs; never echo session cookies.
                errors = [{k: e[k] for k in ('loc', 'msg', 'type')} for e in exc.errors()]
                raise HTTPException(status_code=422, detail=errors) from None
        return handler


router = APIRouter(prefix='/leagues', tags=['League import'], route_class=PrivateInputRoute)


@router.post('/espn/import', response_model=LeagueImport)
def import_league(request: LeagueRequest):
    try:
        data = fetch_league(request)
        # Read settings before fetching the catalog in the league's scoring format.
        settings = parse_league(data, request.model_copy(update={'team_id': None}))
        catalog = current_catalog_for(NflContext(season=2026, target_week=request.week, scoring_format=settings.scoring_format)) if request.team_id is not None else None
        return parse_league(data, request, catalog)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
