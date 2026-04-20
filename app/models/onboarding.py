from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base
import uuid

def generate_user_id():
    return "user_" + uuid.uuid4().hex[:6].upper()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, default=generate_user_id)
    name = Column(String)
    age_group = Column(String)
    occupation = Column(String)

def generate_routine_id():
    return "rtn_" + uuid.uuid4().hex[:6].upper()

class Routine(Base):
    __tablename__ = "routines"
    id = Column(Integer, primary_key=True, index=True)
    routine_id = Column(String, unique=True, default=generate_routine_id)
    user_id = Column(Integer, ForeignKey("users.id"))

    wake_time = Column(String)
    sleep_time = Column(String)
    active_hours = Column(String)
    break_hours = Column(String)

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