from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.db.session import get_db
from app.models.onboarding import User

from app.schemas.locations_schema import LocationBatch

from app.services.intelligence_service import (
    detect_stays,
    detect_location
)

from app.services.intelligence_storage import (
    save_place_visits,
    save_places
)

router = APIRouter()


@router.post("/locations")
def location_events(data: LocationBatch, db: Session = Depends(get_db)):

    print("\n===== LOCATION API START =====")

    if not data.locations:
        raise HTTPException(status_code=400, detail="No locations provided")

    # Get user
    user = db.query(User).filter(User.user_id == data.locations[0].user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user.id

    # Convert timestamps
    locations = []
    for loc in data.locations:
        locations.append({
            "lat": loc.lat,
            "lon": loc.lon,
            "timestamp": datetime.fromisoformat(loc.timestamp)
        })

    print(f"Incoming locations: {len(locations)}")

    # =========================
    # STEP 1: DETECT STAYS
    # =========================
    stays = detect_stays(locations)

    if not stays:
        print("No stays detected")
        return {"message": "no stays detected"}

    print(f"Stays detected: {len(stays)}")

    # =========================
    # STEP 2: SAVE VISITS
    # =========================
    save_place_visits(db, user_id, stays)

    # =========================
    # STEP 3: FETCH ALL VISITS (CRITICAL FIX)
    # =========================
    visits = db.execute(text("""
        SELECT lat, lon, start_time, end_time
        FROM user_place_visits
        WHERE user_id = :user_id
    """), {
        "user_id": user_id
    }).fetchall()

    print(f"Total historical visits: {len(visits)}")

    if not visits:
        return {
            "message": "visits saved but no data for place detection",
            "stays_detected": len(stays)
        }

    # =========================
    # STEP 4: FORMAT FOR DETECTION
    # =========================
    visits_data = []

    for v in visits:
        visits_data.append({
            "lat": float(v[0]),
            "lon": float(v[1]),
            "start_time": v[2],
            "end_time": v[3]
        })

    # =========================
    # STEP 5: DETECT PLACES
    # =========================
    places = detect_location(visits_data)

    print(f"Places detected: {places}")

    # =========================
    # STEP 6: SAVE PLACES
    # =========================
    if places:
        save_places(db, user_id, places)

    print("===== LOCATION API END =====\n")

    return {
        "message": "location processed",
        "stays_detected": len(stays),
        "total_visits": len(visits),
        "places_detected": places
    }