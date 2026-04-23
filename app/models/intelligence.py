from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from app.db.base import Base
from datetime import datetime
import uuid


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
    __tablename__= "user_meal"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    meal_type = Column(String)
    time = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)


class UserPlace(Base):
    __tablename__ = "user_places"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    lat = Column(String)
    lon = Column(String)

    place_type = Column(String) # home/work/etc

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    

class UserPlaceVisit(Base):
    __tablename__ = "user_place_visits"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    place_id = Column(Integer, ForeignKey("user_places.id"))

    start_time = Column(DateTime)
    end_time = Column(DateTime)

    duration = Column(Integer)  # seconds

    created_at = Column(DateTime, default=datetime.utcnow)