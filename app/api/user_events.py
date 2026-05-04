from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Union
from datetime import datetime, timedelta

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

    print("\n========== USER EVENTS API START ==========")

    # ---------------- NORMALIZE INPUT ----------------
    if not isinstance(data, list):
        data = [data]

    if not data:
        raise HTTPException(status_code=400, detail="No events provided")

    print(f"📥 Received {len(data)} events")

    # ---------------- GET USER ----------------
    user = db.query(User).filter(User.user_id == data[0].user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    internal_user_id = user.id

    # ---------------- INSERT EVENTS ----------------
    for event in data:
        print(f"➡️ Inserting: {event.event_type} @ {event.timestamp}")
        create_event(event, db)

    # 🔥 IMPORTANT: commit before reading
    db.commit()

    # ---------------- DETERMINE CORRECT DATE ----------------
    # Use latest event timestamp instead of system time
    latest_event = (
        db.query(UserEvent)
        .filter(UserEvent.user_id == internal_user_id)
        .order_by(UserEvent.timestamp.desc())
        .first()
    )

    if not latest_event:
        print("❌ No events found after insert")
        return {
            "message": "events stored but no data found",
            "screen_behaviour": "insufficient_data",
            "meals_detected": []
        }

    today = latest_event.timestamp.date()

    print(f"📅 Processing date: {today}")

    start = datetime.combine(today, datetime.min.time())
    end = start + timedelta(days=1)

    # ---------------- FETCH EVENTS ----------------
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

    print(f"📊 Fetched {len(events)} events for analysis")

    if not events:
        print("❌ No events in selected window")

        return {
            "message": "events stored but no matching data",
            "screen_behaviour": "insufficient_data",
            "meals_detected": []
        }

    # =========================
    # SCREEN BEHAVIOUR
    # =========================
    screen_result = None

    if len(events) >= 3:
        print("\n📱 Running screen behaviour detection...")

        screen_result = detect_screen_behaviour(events, db)

        if screen_result:
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
            print("⚠️ Screen behaviour returned None")

    else:
        print("⚠️ Too few events for screen behaviour")

    # =========================
    # 🍽️ MEAL DETECTION
    # =========================
    print("\n🍽 Running meal detection...")

    meals = detect_meal(events, db)

    if meals:
        print(f"✅ Meals detected: {meals}")
        save_meals(db, internal_user_id, meals)
    else:
        print("⚠️ No meals detected")

    print("\n========== USER EVENTS API END ==========\n")

    return {
        "message": "events stored & processed",
        "screen_behaviour": screen_result or "insufficient_data",
        "meals_detected": meals or []
    }