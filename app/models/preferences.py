from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base
import uuid

def generate_preference_id():
    return "pfapp_" + uuid.uuid4().hex[:6].upper()

class Preference(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    preference_id = Column(String, unique=True, default=generate_preference_id)
    app_id = Column(Integer, ForeignKey("users.id"))

    app_name = Column(String)
