from app.models.user_events import UserEvent
from app.models.onboarding import User
from datetime import datetime
from app.services.intelligence_service import process_event
import os
from app.workers.tasks import process_event_task

def create_event(data, db, background_tasks=None):

    user = db.query(User).filter(User.user_id == data.user_id).first()
    timestamp = datetime.fromisoformat(
        data.timestamp.replace("Z", "+00:00")
    )

    if not user:
        raise Exception("User not found")

    event = UserEvent(
        user_id=user.id,
        event_type=data.event_type,
        event_data=data.event_data,
        timestamp=timestamp,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    print(f"Event stored: {event.event_type} at {event.timestamp}")

    return event