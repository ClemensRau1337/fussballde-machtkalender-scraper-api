from typing import Optional
from pydantic import BaseModel

class PostalCode(BaseModel):
    postalCode: str
    city: str
    district: Optional[str] = None

class MatchOverview(BaseModel):
    date_label: Optional[str] = None
    time: Optional[str] = None
    age_group: Optional[str] = None
    league: Optional[str] = None
    home: Optional[str] = None
    away: Optional[str] = None
    score: Optional[str] = None
    game_id: Optional[str] = None
    link: Optional[str] = None

class MatchDetail(MatchOverview):
    competition: Optional[str] = None
    league_label: Optional[str] = None
    staffel_id: Optional[str] = None
    spielnummer: Optional[str] = None
    staffelnummer: Optional[str] = None
    venue: Optional[str] = None
    referee: Optional[str] = None
    assistant_1: Optional[str] = None
    assistant_2: Optional[str] = None
