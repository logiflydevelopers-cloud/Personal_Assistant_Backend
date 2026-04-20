from pydantic import BaseModel
from typing import List

class HabitSchema(BaseModel):
    name: str
    frequency: str
    preferred_time: str

class OnboardingSchema(BaseModel):
    name: str
    age_group: str
    occupation: str

    wake_time: str
    sleep_time: str
    active_hours: str
    break_hours: str

    habits: List[HabitSchema]