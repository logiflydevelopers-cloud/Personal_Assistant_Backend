from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

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

    # STEP 1: Detect stays
    stays = detect_stays(locations)

    if not stays:
        print("No stays detected")
        return {"message": "no stays detected"}

    # STEP 2: Save visits
    save_place_visits(db, user_id, stays)

    # STEP 3: Detect places
    places = detect_location(stays)

    if places:
        save_places(db, user_id, places)

    return {
        "message": "location processed",
        "stays_detected": len(stays),
        "places_detected": places
    }