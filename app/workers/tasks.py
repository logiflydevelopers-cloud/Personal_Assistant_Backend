from app.core.celery_app import celery
from app.db.session import SessionLocal
from app.models.user_events import UserEvent
from app.services.intelligence_service import process_event


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=5, retry_kwargs={"max_retries": 3})
def process_event_task(self, event_id: int):

    db = SessionLocal()

    try:
        event = db.query(UserEvent).get(event_id)

        if event:
            process_event(event, db)

    finally:
        db.close()