from typing import List
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import RedirectResponse
from .schemas import MatchOverview, PostalCode, MatchDetail
from .core.postal import get_postal_codes
from .core.calendar import collect_matches_for_area
from .core.match import fetch_match_full

app = FastAPI(title="Fussball.de Matchkalender Scraper API (inoffiziell)", version="1.0.0")

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.get("/postal-codes", response_model=List[PostalCode])
def postal_codes(query: str = Query(description="PLZ/Ort-Query. Gib einen Ort ein und erhalte alle von fussball.de zugeordneten PLZs.")):
    return get_postal_codes(query)

@app.get("/matches", response_model=List[MatchOverview],  response_model_exclude_none=True)
def matches(
    from_: str = Query(..., alias="from", description="YYYY-MM-DD"),
    to: str = Query(..., description="YYYY-MM-DD"),
    area: str = Query(description="Ort oder kommaseparierte PLZs"),
):
    items = collect_matches_for_area(from_, to, area)
    return [
        {
            "date_label": m.get("date_label"),
            "time": m.get("time"),
            "age_group": m.get("age_group"),
            "league": m.get("league"),
            "home": m.get("home"),
            "away": m.get("away"),
            "score": m.get("score"),
            "game_id": m.get("game_id"),
            "link": m.get("link"),
        }
        for m in items
    ]

@app.get("/match", response_model=MatchDetail, response_model_exclude_none=True)
def match_by_link(link: str = Query(..., description="Match-Link (absolut oder relativ)")):
    m = fetch_match_full(link)
    if not m:
        raise HTTPException(status_code=404, detail="Match nicht gefunden oder lesbar")
    return m
