from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base
import uuid

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