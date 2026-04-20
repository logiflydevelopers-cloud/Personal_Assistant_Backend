from sqlalchemy import Column, Integer, String
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