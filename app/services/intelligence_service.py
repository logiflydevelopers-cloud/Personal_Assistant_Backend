from datetime import timedelta
from app.models.user_events import UserEvent

# ------------------ MAIN ENTRY POINT ------------------
def process_event(event, db):
    """
    Central brain of the system.
    Every event passes through here.
    """

    if event.event_type == "unlock":
        detect_wakeup(event, db)


# ------------------ EVENT DETECTION ------------------
def detect_wakeup(event, db):
    """
    Detect wake-up using:
    - time gap
    - morning window
    """

    last_event = (
        db.query(UserEvent)
        .filter(UserEvent.user_id == event.user_id)
        .order_by(UserEvent.timestamp.desc())
        .offset(1)
        .first()
    )

    if not last_event:
        return

    gap = event.timestamp - last_event.timestamp

    score = 0

    # Rule 1: long inactivity
    if gap >= timedelta(hours=5):
        score += 40

    # Rule 2: morning time
    if 4 <= event.timestamp.hour <= 11:
        score += 30

    # Rule 3: check follow-up activity
    recent_events = (
        db.query(UserEvent)
        .filter(
            UserEvent.user_id == event.user_id,
            UserEvent.timestamp >= event.timestamp
        )
        .limit(3)
        .all()
    )

    if len(recent_events) >= 2:
        score += 20

    # FINAL DECISION
    if score >= 60:
        print(f"🔥 Wake-up detected for user {event.user_id} at {event.timestamp}")