from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Float
from app.db.base import Base
from datetime import datetime
from sqlalchemy import UniqueConstraint
import uuid

def generate_user_daily_summary_id():
    return "uds_" + uuid.uuid4().hex[:6].upper()

def generate_user_meals_id():
    return "umeal_" + uuid.uuid4().hex[:6].upper()

def generate_user_palce_id():
    return "uplaces_" + uuid.uuid4().hex[:6].upper()


class UserDailySummary(Base):
    __tablename__ = "user_daily_summary"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    date = Column(DateTime, index=True)

    wake_time = Column(DateTime, nullable=True)
    sleep_time = Column(DateTime, nullable=True)

    total_screen_time = Column(Integer) # seconds
    behaviour_type = Column(String) # focused/distracted/unhealty

    created_at = Column(DateTime, default=datetime.utcnow)


class UserMeal(Base):
    __tablename__ = "user_meals"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    meal_type = Column(String)
    time = Column(DateTime)

    confidence = Column(String)

    created_at = Column(DateTime)


class UserPlace(Base):
    __tablename__ = "user_places"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    lat = Column(Float)
    lon = Column(Float)

    place_type = Column(String) # home/work/etc

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    

class UserPlaceVisit(Base):
    __tablename__ = "user_place_visits"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    lat = Column(Float)
    lon = Column(Float)

    place_id = Column(Integer, ForeignKey("user_places.id"), nullable=True)

    start_time = Column(DateTime)
    end_time = Column(DateTime)

    duration = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)


class UserLocation(Base):
    __tablename__ = "user_locations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    lat = Column(Float)
    lon = Column(Float)

    timestamp = Column(DateTime, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)