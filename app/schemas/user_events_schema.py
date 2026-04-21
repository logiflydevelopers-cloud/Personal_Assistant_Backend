from pydantic import BaseModel
from typing import Dict, Any

class EventCreate(BaseModel):
    user_id: str
    event_type: str
    event_data: Dict[str, Any] = {}
    timestamp: str  # ISO format