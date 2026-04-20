from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base
import uuid

def generate_habit_id():
    return "hbt_" + uuid.uuid4().hex[:6].upper()

class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    habit_id = Column(String, unique=True, default=generate_habit_id)
    user_id = Column(Integer, ForeignKey("users.id"))

    name = Column(String)
    frequency = Column(String)
    preferred_time = Column(String)