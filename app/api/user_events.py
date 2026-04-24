from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.schemas.user_events_schema import EventCreate
from app.services.user_events_services import create_event
from app.db.session import get_db

router = APIRouter()

@router.post("/user-events")
def user_events(
    data: EventCreate,
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    return create_event(data, db, background_tasks)