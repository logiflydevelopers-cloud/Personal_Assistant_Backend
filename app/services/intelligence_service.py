from datetime import timedelta
from collections import defaultdict
from app.models.user_events import UserEvent
from app.services.intelligence_storage import save_wakeup, save_sleep, save_screen_behaviour, save_meals

# ======================================================
# MAIN ENTRY POINT
# ======================================================
def process_event(event, db):
    """
    Central brain of the system.
    Every event passes through here.
    """

    if event.event_type == "unlock":
        detect_wakeup(event, db)

    elif event.event_type == "lock":
        detect_sleep(event, db)


# ======================================================
# EVENT DETECTION
# ======================================================

# ------------------ WAKE-UP ------------------
def detect_wakeup(event, db):

    last_event = (
        db.query(UserEvent)
        .filter(UserEvent.user_id == event.user_id)
        .order_by(UserEvent.timestamp.desc())
        .limit(2)
        .all()
    )

    if len(event) < 2:
        return
    
    last_event = event[1]

    print(f"==============================={last_event}===============================")
    
    if not last_event:
        return

    gap = event.timestamp - last_event.timestamp
    score = 0

    if gap >= timedelta(hours=5):
        score += 40

    if 4 <= event.timestamp.hour <= 11:
        score += 30

    recent_events = (
        db.query(UserEvent)
        .filter(
            UserEvent.user_id == event.user_id,
            UserEvent.timestamp > event.timestamp
        )
        .limit(3)
        .all()
    )

    if len(recent_events) >= 2:
        score += 20

    if score >= 60:

        # Prevent duplicate wakeups
        existing = db.execute("""
            SELECT wake_time FROM user_daily_summary
            WHERE user_id = :user_id AND date = :date
        """, {
            "user_id": event.user_id,
            "date": event.timestamp.date()
        }).fetchone()

        if existing and existing[0]:
            if abs(existing[0] - event.timestamp) < timedelta(minutes=30):
                return

        print(f"Wake-up detected for user {event.user_id} at {event.timestamp}")
        save_wakeup(db, event.user_id, event.timestamp)


# ------------------ SLEEP ------------------
def detect_sleep(event, db):

    last_event = (
        db.query(UserEvent)
        .filter(UserEvent.user_id == event.user_id)
        .order_by(UserEvent.timestamp.desc())
        .limit(2)
        .all()
    )

    if len(event) < 2:
        return
    
    last_event = event[1]

    print(f"==============================={last_event}===============================")

    if not last_event:
        return
    
    gap = event.timestamp - last_event.timestamp
    score = 0

    if gap >= timedelta(hours=5):
        score += 40

    if event.timestamp.hour >= 21 or event.timestamp.hour <= 2:
        score += 30

    if score >= 60:

        # Prevent duplicate sleep entries
        existing = db.execute("""
            SELECT sleep_time FROM user_daily_summary
            WHERE user_id = :user_id AND date = :date
        """, {
            "user_id": event.user_id,
            "date": event.timestamp.date()
        }).fetchone()

        if existing and existing[0]:
            if abs(existing[0] - event.timestamp) < timedelta(minutes=30):
                return

        print(f"Sleep Detected for user {event.user_id} at {event.timestamp}")
        save_sleep(db, event.user_id, event.timestamp)


# ------------------ SCREEN BEHAVIOUR ------------------
def detect_screen_behaviour(event, db):
    """
    event: list of UserEvent sorted by timestamp ASC
    Each event has:
        - event_type (unlock/lock)
        - timestamp (datetime)
    """

    total_screen_time = timedelta()
    unlock_count =0
    short_sessions = 0
    focus_sessions = 0

    sessions = []

    # Build sessions
    for i in range(len(event)-1):
        current = event[i]
        next_event = event[i+1]

        if current.event_type == "unlock" and next_event.event_type == "lock":
            duration = next_event.timestamp - current.timestamp

            sessions.append(duration)
            total_screen_time += duration
            unlock_count +=1

            # short session count
            if duration < timedelta(minutes=5):
                short_sessions += 1

    # Focus session count
    for i in range(len(event)-1):
        gap = event[i+1].timestamp - event[i].timestamp

        if gap >= timedelta(minutes=45) and gap <= timedelta(minutes=90):
            # Ensure daytime
            if 6 <= event[i].timestamp.hour <= 20:
                focus_sessions += 1

    # Late night usage
    late_night_usage = False
    for e in event:
        if e.timestamp.hour >=0 and e.timestamp.hour <= 2:
            late_night_usage = True
            break

    # Distraction detection
    distraction = False

    if unlock_count > 10 and short_sessions / max(unlock_count, 1) > 0.5:
        distraction = True

    # Final decision
    behaviour = "normal"

    if distraction:
        behaviour = "distracted"
    
    if focus_sessions > 0:
        behaviour = "focused"

    if late_night_usage:
        behaviour = "unhealthy"

    # Final Output
    return {
        "total_screen_time": round(total_screen_time.total_seconds()),
        "unlock_count": unlock_count,
        "short_sessions": short_sessions,
        "focus_sessions": focus_sessions,
        "late_night_usage": late_night_usage,
        "behaviour": behaviour
    }


# ------------------ MEAL TIME ------------------
def detect_meal(event, db, is_stationary=True):
    """
    event: list of UserEvent (stored ASC)
    Each event:
        - event_type ("unlock")
        - timestamp (datetime)

    is_stationary: bool (from location/movement layer)
    """

    meals_detected= []

    # Meal time window
    def get_meal_time(hour):
        if 6 <= hour <= 10:
            return "breakfast"
        elif 12 <= hour <= 15:
            return "lunch"
        elif 19 <= hour <= 22:
            return "dinner"
        return None
    
    # Group events into 40-min window
    i = 0
    while i < len(event):
        start_event = event[i]
        window_event = [start_event]

        j = i + 1

        while j < len(event):
            if event[j].timestamp - start_event.timestamp <= timedelta(minutes=40):
                window_event.append(event[j])
                j += 1
            else:
                break

        # Check Rules
        meal_type = get_meal_time(start_event.timestamp.hour)

        if meal_type:
            unlock_count = len(window_event)

            # Rule: Multiple unlock (>=3)
            if unlock_count >= 3:

                # Rule: Stationary (from movement layer)
                if is_stationary:

                    meals_detected.append({
                        "meal_type": meal_type,
                        "time": start_event.timestamp,
                        "confidence": "medium"
                    })

        i = j # move to next window

    return meals_detected

def process_daily_behaviour(user_id, db):
    from datetime import datetime, timedelta

    today = datetime.utcnow().date()
    start = datetime.combine(today, datetime.min.time())
    end = start + timedelta(days=1)

    events = (
        db.query(UserEvent)
        .filter(
            UserEvent.user_id == user_id,
            UserEvent.timestamp >= start,
            UserEvent.timestamp < end
        )
        .order_by(UserEvent.timestamp.asc())
        .all()
    )

    if not events:
        return

    # Screen behaviour
    result = detect_screen_behaviour(events, db)
    save_screen_behaviour(db, user_id, result, today)

    # Meals detection
    meals = detect_meal(events, db)
    if meals:
        save_meals(db, user_id, meals)


# ------------------ ACTIVITY ------------------
def detect_activity(event, db, locations):
    """
    event: list of events (stored ASC)
        - timestamp
        - event_type
    
    locations: list of location points (samr order)
        - latitude
        - longitude
        - timestamp
    """

    results = []

    # Helper: calculate distance (basic approximation)
    def distance(loc1, loc2):
        return ((loc1["lat"] - loc2["lat"])**2 + (loc1["lon"] - loc2["lon"])**2) ** 0.5
    
    # Detect still vs travelling
    for i in range(len(locations) - 1):
        current = locations[i]
        next_loc = locations[i + 1]

        time_gap = next_loc["timestamp"] - current["timestamp"]
        dist = distance(current, next_loc)

        # Still
        if dist < 0.0005:
            results.append({
                "type": "still",
                "time": current["timestamp"]
            })
        
        # Travelling
        if dist >= 0.0005 and time_gap <= timedelta(minutes=10):
            results.append({
                "type": "travelling",
                "time": current["timestamp"]
            })
    
    return results

# ------------------ LOCATION ------------------
def detect_location(visits):
    """
    visits: list of dicts
        {
            "lat": float,
            "lon": float,
            "start_time": datetime,
            "end_time": datetime
        }
    """

    place_stats = defaultdict(lambda: {
        "visits": 0,
        "total_duration": timedelta(),
        "time_slots": []
    })

    # Aggregate locations
    for visit in visits:
        key = (round(visit["lat"], 3), round(visit["lon"], 3))

        duration = visit["end_time"] - visit["start_time"]

        place_stats[key]["visits"] += 1
        place_stats[key]["total_duration"] += duration
        place_stats[key]["time_slots"].append(visit["start_time"])

    results = []

    # Detect Place types
    for place, data in place_stats.items():
        visits_counts = data["visits"]
        total_duration = data["total_duration"]
        avg_duration = total_duration / visits_counts

        hours = [t.hour for t in data["time_slots"]]

        # Home detection
        if (
            any(0 <= h <= 6 for h in hours) and
            avg_duration >= timedelta(hours=6) and
            visits_counts >= 3
        ):
            results.append({
                "place": place,
                "type": "home"
            })
            continue

        # Work place
        if (
            any(9 <= h <= 18 for h in hours) and
            timedelta(hours=4) <= avg_duration <= timedelta(hours=8) and
            visits_counts >=3
        ):
            results.append({
                "place": place,
                "type": "work"
            })

        # Activity place
        if (
            timedelta(hours=1) <= avg_duration <= timedelta(hours=2) and
            visits_counts >= 3
        ):
            results.append({
                "place": place,
                "type": "activity_place"
            })
            continue

        # Meal place
        if (
            timedelta(minutes=30) <= avg_duration <= timedelta(hours=1) and
            visits_counts <= 3
        ):
            results.append({
                "place": place,
                "type": "meal_place"
            })
            continue

    return results