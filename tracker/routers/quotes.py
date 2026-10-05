from typing import Optional
from fastapi import APIRouter

from tracker.core.quotes import get_quotes, ALL_THEMES

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("")
def list_quotes(theme: Optional[str] = None):
    return {"themes": ALL_THEMES, "quotes": get_quotes(theme)}
