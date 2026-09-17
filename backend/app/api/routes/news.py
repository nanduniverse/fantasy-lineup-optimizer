from fastapi import APIRouter
from app.services.news import get_news

router = APIRouter(tags=["news"])


@router.get("/news")
def news():
    return get_news()
