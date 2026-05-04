from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Time, Float, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime
import uuid


# ------------------ USER ------------------

def generate_user_id():
    return "user_" + uuid.uuid4().hex[:6].upper()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, default=generate_user_id)

    name = Column(String)
    age_group = Column(String)
    occupation = Column(String)

    routines = relationship("Routine", back_populates="user", cascade="all, delete")
    habits = relationship("Habit", back_populates="user", cascade="all, delete")

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ------------------ ROUTINE ------------------

def generate_routine_id():
    return "rtn_" + uuid.uuid4().hex[:6].upper()


class Routine(Base):
    __tablename__ = "routines"

    id = Column(Integer, primary_key=True, index=True)
    routine_id = Column(String, unique=True, default=generate_routine_id)

    user_id = Column(Integer, ForeignKey("users.id"))

    wake_time = Column(Time)
    sleep_time = Column(Time)

    active_hours = Column(Float)
    break_hours = Column(Float)

    hobby_hours = Column(Float)

    user = relationship("User", back_populates="routines")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ------------------ HABIT ------------------

def generate_habit_id():
    return "hbt_" + uuid.uuid4().hex[:6].upper()


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    habit_id = Column(String, unique=True, default=generate_habit_id)

    user_id = Column(Integer, ForeignKey("users.id"))

    name = Column(String)
    frequency = Column(String)
    preferred_time = Column(Time)  
    
    user = relationship("User", back_populates="habits")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)