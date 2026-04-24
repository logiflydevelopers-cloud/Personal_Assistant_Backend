from app.models.user_events import UserEvent
from app.models.onboarding import User
from datetime import datetime
from app.workers.tasks import process_event_task

def create_event(data, db):

    user = db.query(User).filter(User.user_id == data.user_id).first()

    if not user:
        raise Exception("User not found")

    event = UserEvent(
        user_id=user.id,
        event_type=data.event_type,
        event_data=data.event_data,
        timestamp=datetime.fromisoformat(data.timestamp)
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    # Send to Celery
    process_event_task.delay(event.id)

    return {"message": "event stored"}