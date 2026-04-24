from datetime import timedelta
from sqlalchemy import text
from collections import defaultdict
from app.models.user_events import UserEvent
from app.services.intelligence_storage import save_wakeup, save_sleep, save_screen_behaviour, save_meals
import math

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

    print("\n===== WAKEUP DETECTION START =====")

    events = (
        db.query(UserEvent)
        .filter(UserEvent.user_id == event.user_id)
        .order_by(UserEvent.timestamp.desc())
        .limit(2)
        .all()
    )

    print(f"Fetched events count: {len(events)}")

    if len(events) < 2:
        print("Not enough events for wakeup detection")
        return

    # Use current event explicitly
    latest_event = event
    previous_event = events[1]

    print(f"Prev: {previous_event.timestamp}, Curr: {latest_event.timestamp}")

    if latest_event.timestamp == previous_event.timestamp:
        print("Duplicate timestamps → skipping")
        return

    gap = latest_event.timestamp - previous_event.timestamp
    print(f"GAP: {gap}")

    score = 0

    if gap >= timedelta(hours=5):
        score += 40
        print("Score +40 (long inactivity)")

    if 4 <= latest_event.timestamp.hour <= 11:
        score += 30
        print("Score +30 (morning time)")

    next_events = (
        db.query(UserEvent)
        .filter(
            UserEvent.user_id == event.user_id,
            UserEvent.timestamp > latest_event.timestamp
        )
        .order_by(UserEvent.timestamp.asc())
        .limit(3)
        .all()
    )

    print(f"Next events count: {len(next_events)}")

    if len(next_events) >= 2:
        score += 20
        print("Score +20 (continued activity)")

    print(f"FINAL WAKE SCORE: {score}")

    if score < 60:
        print("Wakeup NOT detected (score too low)")
        return

    print("Wakeup condition PASSED")

    existing = db.execute(text("""
        SELECT wake_time FROM user_daily_summary
        WHERE user_id = :user_id AND date = :date
    """), {
        "user_id": event.user_id,
        "date": latest_event.timestamp.date()
    }).fetchone()

    print(f"Existing wake entry: {existing}")

    if existing and existing[0]:
        if abs(existing[0] - latest_event.timestamp) < timedelta(minutes=30):
            print("Duplicate wakeup detected → skipping")
            return

    print(f"Saving wakeup for user {event.user_id} at {latest_event.timestamp}")

    save_wakeup(db, event.user_id, latest_event.timestamp)

    print("===== WAKEUP DETECTION END =====\n")


# ------------------ SLEEP ------------------
def detect_sleep(event, db):

    print("\n===== SLEEP DETECTION START =====")

    events = (
        db.query(UserEvent)
        .filter(UserEvent.user_id == event.user_id)
        .order_by(UserEvent.timestamp.desc())
        .limit(2)
        .all()
    )

    print(f"Fetched events count: {len(events)}")

    if len(events) < 2:
        print("Not enough events for sleep detection")
        return

    latest_event = event
    previous_event = events[1]

    print(f"Prev: {previous_event.timestamp}, Curr: {latest_event.timestamp}")

    if latest_event.timestamp == previous_event.timestamp:
        print("Duplicate timestamps → skipping")
        return

    gap = latest_event.timestamp - previous_event.timestamp
    print(f"GAP: {gap}")

    score = 0

    if gap >= timedelta(hours=5):
        score += 40
        print("Score +40 (long inactivity)")

    if latest_event.timestamp.hour >= 21 or latest_event.timestamp.hour <= 2:
        score += 30
        print("Score +30 (night time)")

    print(f"FINAL SLEEP SCORE: {score}")

    if score < 60:
        print("Sleep NOT detected (score too low)")
        return

    print("Sleep condition PASSED")

    # assign correct sleep date
    sleep_date = latest_event.timestamp.date()
    if latest_event.timestamp.hour <= 3:
        sleep_date = sleep_date - timedelta(days=1)

    existing = db.execute(text("""
        SELECT sleep_time FROM user_daily_summary
        WHERE user_id = :user_id AND date = :date
    """), {
        "user_id": event.user_id,
        "date": sleep_date
    }).fetchone()

    print(f"Existing sleep entry: {existing}")

    if existing and existing[0]:
        if abs(existing[0] - latest_event.timestamp) < timedelta(minutes=30):
            print("Duplicate sleep detected → skipping")
            return

    print(f"Saving sleep for user {event.user_id} at {latest_event.timestamp}")

    save_sleep(db, event.user_id, latest_event.timestamp)

    print("===== SLEEP DETECTION END =====\n")

# ------------------ SCREEN BEHAVIOUR ------------------
def detect_screen_behaviour(events, db):

    print("\n===== SCREEN BEHAVIOUR DETECTION START =====")

    if not events or len(events) < 2:
        print("Not enough events to analyze")
        return

    print(f"Total events received: {len(events)}")

    total_screen_time = timedelta()
    unlock_count = 0
    short_sessions = 0
    focus_sessions = 0

    sessions = []

    # ------------------ SESSION BUILDING ------------------
    print("\n--- Building Sessions ---")

    for i in range(len(events) - 1):
        current = events[i]
        next_event = events[i + 1]

        print(f"[{i}] {current.event_type} → {next_event.event_type}")

        if current.event_type == "unlock" and next_event.event_type == "lock":
            duration = next_event.timestamp - current.timestamp

            print(f"Session detected: {duration}")

            sessions.append(duration)
            total_screen_time += duration
            unlock_count += 1

            if duration < timedelta(minutes=5):
                short_sessions += 1
                print("Short session detected")

    print(f"\nTotal sessions: {len(sessions)}")
    print(f"Total screen time: {total_screen_time}")
    print(f"Unlock count: {unlock_count}")
    print(f"Short sessions: {short_sessions}")

    # ------------------ FOCUS SESSIONS ------------------
    print("\n--- Detecting Focus Sessions ---")

    for i in range(len(events) - 1):
        gap = events[i + 1].timestamp - events[i].timestamp

        print(f"Gap {i}: {gap}")

        if timedelta(minutes=45) <= gap <= timedelta(minutes=90):
            if 6 <= events[i].timestamp.hour <= 20:
                focus_sessions += 1
                print("Focus session detected")

    print(f"Focus sessions: {focus_sessions}")

    # ------------------ LATE NIGHT USAGE ------------------
    print("\n--- Checking Late Night Usage ---")

    late_night_usage = False

    for e in events:
        print(f"Event hour: {e.timestamp.hour}")

        if 0 <= e.timestamp.hour <= 2:
            late_night_usage = True
            print("Late night usage detected")
            break

    print(f"Late night usage: {late_night_usage}")

    # ------------------ DISTRACTION DETECTION ------------------
    print("\n--- Detecting Distraction ---")

    distraction = False

    if unlock_count > 0:
        ratio = short_sessions / unlock_count
    else:
        ratio = 0

    print(f"Short session ratio: {ratio}")

    if unlock_count > 10 and ratio > 0.5:
        distraction = True
        print("User is distracted")

    print(f"Distraction: {distraction}")

    # ------------------ FINAL DECISION ------------------
    print("\n--- Final Behaviour Decision ---")

    behaviour = "normal"

    if distraction:
        behaviour = "distracted"
        print("Behaviour → distracted")

    if focus_sessions > 0:
        behaviour = "focused"
        print("Behaviour → focused (overrides distracted)")

    if late_night_usage:
        behaviour = "unhealthy"
        print("Behaviour → unhealthy (highest priority)")

    print("\n===== FINAL RESULT =====")
    print(f"Total screen time (sec): {round(total_screen_time.total_seconds())}")
    print(f"Unlock count: {unlock_count}")
    print(f"Short sessions: {short_sessions}")
    print(f"Focus sessions: {focus_sessions}")
    print(f"Late night usage: {late_night_usage}")
    print(f"Final behaviour: {behaviour}")

    print("===== SCREEN BEHAVIOUR DETECTION END =====\n")

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

    print("\n===== MEAL DETECTION START =====")

    meals_detected = []

    def get_meal_time(hour):
        if 6 <= hour <= 10:
            return "breakfast"
        elif 12 <= hour <= 15:
            return "lunch"
        elif 19 <= hour <= 22:
            return "dinner"
        return None

    print(f"Total events received: {len(event)}")

    i = 0
    while i < len(event):

        start_event = event[i]
        print(f"\n--- New Window Start ---")
        print(f"Start time: {start_event.timestamp}")

        window_event = [start_event]
        j = i + 1

        # Build 40-min window
        while j < len(event):
            time_diff = event[j].timestamp - start_event.timestamp

            if time_diff <= timedelta(minutes=40):
                window_event.append(event[j])
                print(f"Adding event at {event[j].timestamp} (Δ {time_diff})")
                j += 1
            else:
                break

        print(f"Window size: {len(window_event)}")

        # Determine meal type
        meal_type = get_meal_time(start_event.timestamp.hour)
        print(f"Detected meal window type: {meal_type}")

        if meal_type:

            unlock_count = len(window_event)
            print(f"Unlock count in window: {unlock_count}")

            # Rule: Multiple unlock (>=3)
            if unlock_count >= 3:
                print("Rule passed: multiple unlocks")

                # Rule: Stationary
                print(f"Stationary status: {is_stationary}")

                if is_stationary:
                    print("Rule passed: stationary")

                    meal = {
                        "meal_type": meal_type,
                        "time": start_event.timestamp,
                        "confidence": "medium"
                    }

                    print(f"Meal detected: {meal}")

                    meals_detected.append(meal)

                else:
                    print("Skipped: not stationary")

            else:
                print("Skipped: not enough unlocks")

        else:
            print("Skipped: not in meal time window")

        i = j  # move to next window

    print(f"\nTotal meals detected: {len(meals_detected)}")
    print("===== MEAL DETECTION END =====\n")

    return meals_detected

def process_daily_behaviour(user_id, db):
    from datetime import datetime, timedelta

    print("\n===== DAILY BEHAVIOUR PROCESSING START =====")

    # Use LOCAL TIME
    today = datetime.now().date()

    start = datetime.combine(today, datetime.min.time())
    end = start + timedelta(days=1)

    print(f"Processing date: {today}")
    print(f"Window: {start} → {end}")

    # Fetch events
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

    print(f"Fetched {len(events)} events")

    if not events:
        print("No events found → skipping")
        return

    # ------------------ SCREEN ------------------
    print("\n--- SCREEN BEHAVIOUR ---")

    result = detect_screen_behaviour(events, db)

    print(f"Screen result: {result}")

    save_screen_behaviour(
        db,
        user_id,
        {
            "total_screen_time_seconds": result["total_screen_time"],
            "behaviour": result["behaviour"]
        },
        today
    )

    # ------------------ MEALS ------------------
    print("\n--- MEAL DETECTION ---")

    meals = detect_meal(events, db)

    print(f"Meals detected: {meals}")

    if meals:
        save_meals(db, user_id, meals)

    print("===== DAILY BEHAVIOUR PROCESSING END =====\n")


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
def detect_stays(locations):
    """
    locations: list of dicts (sorted ASC)
    [
        {"lat": float, "lon": float, "timestamp": datetime}
    ]
    """

    print("\n===== STAY DETECTION START =====")

    stays = []

    if not locations or len(locations) < 2:
        print("Not enough location points")
        return stays

    # distance function (Haversine simplified)
    def distance(p1, p2):
        return math.sqrt(
            (p1["lat"] - p2["lat"]) ** 2 +
            (p1["lon"] - p2["lon"]) ** 2
        )

    DIST_THRESHOLD = 0.001       # ~100 meters
    TIME_THRESHOLD = timedelta(minutes=10)

    i = 0

    while i < len(locations) - 1:

        start = locations[i]
        cluster = [start]

        j = i + 1

        while j < len(locations):
            dist = distance(start, locations[j])

            if dist <= DIST_THRESHOLD:
                cluster.append(locations[j])
                j += 1
            else:
                break

        # Calculate duration
        start_time = cluster[0]["timestamp"]
        end_time = cluster[-1]["timestamp"]
        duration = end_time - start_time

        print(f"\nCluster from {start_time} → {end_time}")
        print(f"Points: {len(cluster)}, Duration: {duration}")

        # Stay condition
        if duration >= TIME_THRESHOLD:
            avg_lat = sum(p["lat"] for p in cluster) / len(cluster)
            avg_lon = sum(p["lon"] for p in cluster) / len(cluster)

            stays.append({
                "lat": avg_lat,
                "lon": avg_lon,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration
            })

            print("→ STAY DETECTED")

        i = j  # jump forward

    print("\n===== STAY DETECTION END =====\n")

    return stays

def detect_location(visits):

    print("\n===== PLACE DETECTION START =====")

    place_stats = defaultdict(lambda: {
        "visits": 0,
        "total_duration": timedelta(),
        "time_slots": []
    })

    def is_same_place(lat1, lon1, lat2, lon2, threshold=0.001):
        return abs(lat1 - lat2) <= threshold and abs(lon1 - lon2) <= threshold

    # -----------------------------
    # Aggregate locations
    # -----------------------------
    for visit in visits:

        visit_key = (round(visit["lat"], 3), round(visit["lon"], 3))
        matched_key = None

        for key in place_stats:
            if is_same_place(visit_key[0], visit_key[1], key[0], key[1]):
                matched_key = key
                break

        if not matched_key:
            matched_key = visit_key

        duration = visit["end_time"] - visit["start_time"]

        place_stats[matched_key]["visits"] += 1
        place_stats[matched_key]["total_duration"] += duration
        place_stats[matched_key]["time_slots"].append(visit["start_time"])

    results = []

    # -----------------------------
    # Classification
    # -----------------------------
    for place, data in place_stats.items():

        visits_counts = data["visits"]
        total_duration = data["total_duration"]
        avg_duration = total_duration / visits_counts
        hours = [t.hour for t in data["time_slots"]]

        print(f"\nAnalyzing place: {place}")
        print(f"Visits: {visits_counts}, Avg Duration: {avg_duration}")

        # HOME
        if (
            any(0 <= h <= 6 for h in hours) and
            avg_duration >= timedelta(hours=5) and
            visits_counts >= 3
        ):
            results.append({"place": place, "type": "home"})
            print("→ HOME")
            continue

        # WORK
        if (
            any(9 <= h <= 18 for h in hours) and
            timedelta(hours=4) <= avg_duration <= timedelta(hours=9) and
            visits_counts >= 3
        ):
            results.append({"place": place, "type": "work"})
            print("→ WORK")
            continue

        # ACTIVITY
        if (
            timedelta(hours=1) <= avg_duration <= timedelta(hours=2) and
            visits_counts >= 3
        ):
            results.append({"place": place, "type": "activity_place"})
            print("→ ACTIVITY")
            continue

        # MEAL
        if (
            timedelta(minutes=30) <= avg_duration <= timedelta(hours=1) and
            visits_counts >= 3
        ):
            results.append({"place": place, "type": "meal_place"})
            print("→ MEAL")
            continue

        # FALLBACK
        results.append({"place": place, "type": "unknown"})
        print("→ UNKNOWN")

    print("\n===== PLACE DETECTION END =====\n")

    return results