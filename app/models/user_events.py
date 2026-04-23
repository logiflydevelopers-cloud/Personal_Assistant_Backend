from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime
import uuid

# ------------------ EVENTS ------------------

def generate_event_id():
    return "event_" + uuid.uuid4().hex[:6].upper()


class UserEvent(Base):
    __tablename__ = "user_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, default=generate_event_id)
    user_id = Column(Integer, ForeignKey("users.id"))

    event_type = Column(String, index=True)

    event_data = Column(JSON)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    