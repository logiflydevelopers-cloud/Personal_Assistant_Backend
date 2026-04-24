from pydantic import BaseModel
from typing import List

class LocationPoint(BaseModel):
    user_id: str
    lat: float
    lon: float
    timestamp: str

class LocationBatch(BaseModel):
    locations: List[LocationPoint]