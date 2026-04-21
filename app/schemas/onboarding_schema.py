from pydantic import BaseModel
from typing import List

class Habit(BaseModel):
    name: str
    frequency: str
    preferred_time: str

class Onboarding(BaseModel):
    name: str
    age_group: str
    occupation: str

    wake_time: str
    sleep_time: str
    active_hours: float
    break_hours: float

    habits: List[Habit]