from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.user_events_schema import EventCreate
from app.services.user_events_services import create_event
from app.db.session import get_db

router = APIRouter()

@router.post("/user-events")
def onboarding(data: EventCreate, db: Session = Depends(get_db)):
    return create_event(data, db)
