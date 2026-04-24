from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Union

from app.schemas.user_events_schema import EventCreate
from app.services.user_events_services import create_event
from app.db.session import get_db
from app.models.onboarding import User
from app.models.user_events import UserEvent

from app.services.intelligence_service import (
    detect_screen_behaviour,
    detect_meal
)

from app.services.intelligence_storage import (
    save_screen_behaviour,
    save_meals
)

router = APIRouter()


@router.post("/user-events")
def user_events(
    data: Union[EventCreate, List[EventCreate]],
    db: Session = Depends(get_db)
):

    # Normalize input
    if not isinstance(data, list):
        data = [data]

    # Get user
    user = db.query(User).filter(User.user_id == data[0].user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    internal_user_id = user.id

    # Insert events (this already triggers wake/sleep internally)
    for event in data:
        create_event(event, db)

    # Fetch ONLY today's events
    from datetime import datetime, timedelta

    today = datetime.now().date()
    start = datetime.combine(today, datetime.min.time())
    end = start + timedelta(days=1)

    events = (
        db.query(UserEvent)
        .filter(
            UserEvent.user_id == internal_user_id,
            UserEvent.timestamp >= start,
            UserEvent.timestamp < end
        )
        .order_by(UserEvent.timestamp.asc())
        .all()
    )

    print(f"\nFetched {len(events)} events for analysis (today)")

    # =========================
    # 📱 SCREEN BEHAVIOUR
    # =========================
    screen_result = None

    if len(events) >= 3:  # avoid noise
        screen_result = detect_screen_behaviour(events, db)

        if screen_result and screen_result.get("behaviour") != "insufficient_data":
            save_screen_behaviour(
                db,
                internal_user_id,
                {
                    "total_screen_time": screen_result["total_screen_time"],
                    "behaviour": screen_result["behaviour"]
                },
                today
            )
        else:
            print("Skipping screen save (not enough data)")
    else:
        print("Too few events for screen behaviour")

    # =========================
    # 🍽️ MEAL DETECTION (NEW)
    # =========================
    meals = detect_meal(events, db)

    if meals:
        print(f"Meals detected: {meals}")
        save_meals(db, internal_user_id, meals)
    else:
        print("No meals detected")

    # REMOVED
    # detect_sleep / detect_wakeup
    # Already handled inside create_event()

    return {
        "message": "events stored & processed",
        "screen_behaviour": screen_result or "insufficient_data",
        "meals_detected": meals or []
    }