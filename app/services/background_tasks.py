from app.db.session import SessionLocal
from app.models.user_events import UserEvent
from app.services.intelligence_service import process_event


def process_event_safe(event_id: int):
    db = SessionLocal()

    try:
        event = db.query(UserEvent).get(event_id)

        if event:
            process_event(event, db)

    except Exception as e:
        print(f"Error in background task: {e}")

    finally:
        db.close()