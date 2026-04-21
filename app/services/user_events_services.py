from app.models.user_events import UserEvent
from app.models.onboarding import User
from datetime import datetime
from app.services.intelligence_service import process_event


def create_event(data, db):
    # Convert public user_id → internal id
    user = db.query(User).filter(User.user_id == data.user_id).first()

    if not user:
        raise Exception("User not found")

    # Create event
    event = UserEvent(
        user_id=user.id,  
        event_type=data.event_type,
        event_data=data.event_data,
        timestamp=datetime.fromisoformat(data.timestamp)
    )

    # Save to DB
    db.add(event)
    db.commit()
    db.refresh(event)  

    # Trigger intelligence layer
    process_event(event, db)

    return {"message": "event stored"}