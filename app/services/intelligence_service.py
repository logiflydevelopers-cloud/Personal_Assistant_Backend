from datetime import timedelta, datetime
from sqlalchemy import text
from collections import defaultdict
from app.models.user_events import UserEvent
from app.services.intelligence_storage import (
    save_wakeup, save_sleep, save_screen_behaviour, save_meals
)

# ======================================================
# CONFIG
# ======================================================
SCREEN_EVENTS = {"unlock", "lock", "app_open"}
FOCUS_MIN = timedelta(minutes=45)
FOCUS_MAX = timedelta(minutes=90)


# ======================================================
# ENTRY POINT (FIXED: NO DAILY CALL HERE)
# ======================================================
def process_event(event, db):
    print(f"\n⚡ Processing event: {event.event_type} @ {event.timestamp}")

    if event.event_type == "unlock":
        detect_wakeup(event, db)

    elif event.event_type == "lock":
        detect_sleep(event, db)

    # ❌ REMOVED daily processing from here
    # Daily pipeline should be triggered AFTER batch insert


# ======================================================
# HELPERS
# ======================================================
def normalize_events(events):
    print("\n🔧 Normalizing events...")

    events = sorted(events, key=lambda x: x.timestamp)

    cleaned = []
    seen = set()

    for e in events:
        # safer unique key (avoid accidental drops)
        key = (e.event_type, e.timestamp, getattr(e, "id", None))

        if key not in seen:
            cleaned.append(e)
            seen.add(key)

    filtered = [e for e in cleaned if e.event_type in SCREEN_EVENTS]

    print(f"➡️ {len(filtered)} events after normalization")
    return filtered


# ======================================================
# WAKEUP DETECTION (UNCHANGED LOGIC)
# ======================================================
def detect_wakeup(event, db):

    events = db.query(UserEvent)\
        .filter(UserEvent.user_id == event.user_id)\
        .order_by(UserEvent.timestamp.desc())\
        .limit(3)\
        .all()

    if len(events) < 2:
        return

    prev = events[1]
    gap = event.timestamp - prev.timestamp

    if gap < timedelta(hours=4):
        return

    if not (5 <= event.timestamp.hour <= 11):
        return

    existing = db.execute(text("""
        SELECT wake_time FROM user_daily_summary
        WHERE user_id = :user_id AND date = :date
    """), {
        "user_id": event.user_id,
        "date": event.timestamp.date()
    }).fetchone()

    if existing and existing[0]:
        return

    print(f"🌅 Wakeup detected at {event.timestamp}")
    save_wakeup(db, event.user_id, event.timestamp)


# ======================================================
# SLEEP DETECTION (UNCHANGED LOGIC)
# ======================================================
def detect_sleep(event, db):

    events = db.query(UserEvent)\
        .filter(UserEvent.user_id == event.user_id)\
        .order_by(UserEvent.timestamp.desc())\
        .limit(3)\
        .all()

    if len(events) < 2:
        return

    prev = events[1]
    gap = event.timestamp - prev.timestamp

    if gap < timedelta(hours=4):
        return

    if not (event.timestamp.hour >= 21 or event.timestamp.hour <= 3):
        return

    sleep_date = event.timestamp.date()
    if event.timestamp.hour <= 3:
        sleep_date -= timedelta(days=1)

    existing = db.execute(text("""
        SELECT sleep_time FROM user_daily_summary
        WHERE user_id = :user_id AND date = :date
    """), {
        "user_id": event.user_id,
        "date": sleep_date
    }).fetchone()

    if existing and existing[0]:
        return

    print(f"🌙 Sleep detected at {event.timestamp}")
    save_sleep(db, event.user_id, event.timestamp)


# ======================================================
# SCREEN BEHAVIOUR (UNCHANGED LOGIC + CLEAN LOGS)
# ======================================================
def detect_screen_behaviour(events, db):

    print("\n========== SCREEN BEHAVIOUR ==========")

    if not events:
        print("❌ No events received")
        return None

    print(f"📦 Raw events: {len(events)}")

    events = normalize_events(events)

    if not events:
        print("❌ No valid events after normalization")
        return None

    sessions = []
    current_start = None

    for e in events:
        if e.event_type == "unlock":
            current_start = e.timestamp

        elif e.event_type == "lock" and current_start:
            if e.timestamp > current_start:
                sessions.append((current_start, e.timestamp))
            current_start = None

    if current_start:
        sessions.append((current_start, events[-1].timestamp))

    if not sessions:
        print("❌ No sessions built")
        return None

    total_screen = timedelta()
    short_sessions = 0

    for start, end in sessions:
        duration = end - start
        total_screen += duration

        if duration < timedelta(minutes=5):
            short_sessions += 1

    unlock_count = len(sessions)

    focus_sessions = 0
    for i in range(len(sessions) - 1):
        gap = sessions[i+1][0] - sessions[i][1]
        if FOCUS_MIN <= gap <= FOCUS_MAX:
            focus_sessions += 1

    late_night = any(
        (0 <= s[0].hour <= 2) and (s[1] - s[0] > timedelta(minutes=20))
        for s in sessions
    )

    ratio = short_sessions / unlock_count if unlock_count else 0
    distracted = unlock_count >= 5 and ratio > 0.4

    behaviour = "normal"

    if total_screen > timedelta(hours=5):
        behaviour = "overuse"

    if late_night and total_screen > timedelta(hours=2):
        behaviour = "unhealthy"

    elif focus_sessions >= 2:
        behaviour = "focused"

    elif distracted:
        behaviour = "distracted"

    result = {
        "total_screen_time": int(total_screen.total_seconds()),
        "unlock_count": unlock_count,
        "short_sessions": short_sessions,
        "focus_sessions": focus_sessions,
        "late_night_usage": late_night,
        "behaviour": behaviour
    }

    print("✅ Screen behaviour:", result)
    return result


# ======================================================
# MEAL DETECTION (FIXED WINDOW SKIP)
# ======================================================
from datetime import timedelta

def detect_meal(events, db, is_stationary=True):

    print("\n========== MEAL DETECTION ==========")

    meals_detected = []

    def get_meal_time(hour):
        if 6 <= hour <= 10:
            return "breakfast"
        elif 12 <= hour <= 15:
            return "lunch"
        elif 19 <= hour <= 22:
            return "dinner"
        return None

    i = 0
    while i < len(events):

        start_event = events[i]
        window_event = [start_event]
        j = i + 1

        # ---------------- WINDOW BUILD ----------------
        while j < len(events):
            if (events[j].timestamp - start_event.timestamp) <= timedelta(minutes=40):
                window_event.append(events[j])
                j += 1
            else:
                break

        meal_type = get_meal_time(start_event.timestamp.hour)

        # ---------------- DETECTION ----------------
        if meal_type and len(window_event) >= 3 and is_stationary:
            meal = {
                "meal_type": meal_type,
                "time": start_event.timestamp,
                "confidence": "medium"
            }
            meals_detected.append(meal)

        i += 1  # sliding window

    print(f"\n🔎 Raw meals detected: {len(meals_detected)}")

    # ======================================================
    # 🔥 SMART DEDUPLICATION (SESSION-BASED)
    # ======================================================
    meals_detected.sort(key=lambda x: x["time"])

    unique_meals = []

    for meal in meals_detected:

        if not unique_meals:
            unique_meals.append(meal)
            continue

        last_meal = unique_meals[-1]
        time_diff = meal["time"] - last_meal["time"]

        # 🚀 CORE LOGIC
        if (
            meal["meal_type"] == last_meal["meal_type"]
            and time_diff <= timedelta(hours=3)
        ):
            print(f"⚠️ Skipping duplicate {meal['meal_type']} at {meal['time']}")
            continue

        unique_meals.append(meal)

    print(f"🧹 Deduplicated meals: {len(unique_meals)}")

    print("\n🍽 FINAL MEALS:")
    for m in unique_meals:
        print(m)

    return unique_meals


# ======================================================
# DAILY PIPELINE (FINAL FIX)
# ======================================================
def process_daily_behaviour(user_id, db):

    print("\n🚀 Running daily pipeline...")

    events = db.query(UserEvent)\
        .filter(UserEvent.user_id == user_id)\
        .order_by(UserEvent.timestamp.asc())\
        .all()

    if not events:
        print("❌ No events found")
        return

    print(f"📊 Total events fetched: {len(events)}")

    today = events[-1].timestamp.date()

    screen = detect_screen_behaviour(events, db)

    if screen:
        save_screen_behaviour(db, user_id, screen, today)

    meals = detect_meal(events, db)

    if meals:
        save_meals(db, user_id, meals)

# ======================================================
# LOCATION (UNCHANGED CLEAN)
# ======================================================
def detect_stays(locations):

    if len(locations) < 2:
        return []

    locations = sorted(locations, key=lambda x: x["timestamp"])

    stays = []
    DIST = 0.001
    TIME = timedelta(minutes=10)

    def dist(a, b):
        return ((a["lat"] - b["lat"])**2 + (a["lon"] - b["lon"])**2) ** 0.5

    i = 0
    while i < len(locations) - 1:

        cluster = [locations[i]]
        j = i + 1

        while j < len(locations) and dist(locations[i], locations[j]) <= DIST:
            cluster.append(locations[j])
            j += 1

        duration = cluster[-1]["timestamp"] - cluster[0]["timestamp"]

        if duration >= TIME:
            stays.append({
                "lat": locations[i]["lat"],
                "lon": locations[i]["lon"],
                "start_time": cluster[0]["timestamp"],
                "end_time": cluster[-1]["timestamp"],
                "duration": duration
            })

        i = j

    return stays


def detect_location(visits):

    stats = defaultdict(lambda: {
        "visits": 0,
        "total": timedelta(),
        "hours": []
    })

    for v in visits:
        key = (round(v["lat"], 3), round(v["lon"], 3))

        stats[key]["visits"] += 1
        stats[key]["total"] += (v["end_time"] - v["start_time"])
        stats[key]["hours"].append(v["start_time"].hour)

    results = []

    for place, data in stats.items():

        avg = data["total"] / data["visits"]

        if any(0 <= h <= 6 for h in data["hours"]) and avg >= timedelta(hours=5):
            results.append({"place": place, "type": "home"})

        elif any(9 <= h <= 18 for h in data["hours"]) and timedelta(hours=4) <= avg <= timedelta(hours=9):
            results.append({"place": place, "type": "work"})

        elif timedelta(hours=1) <= avg <= timedelta(hours=2):
            results.append({"place": place, "type": "activity_place"})

        elif timedelta(minutes=30) <= avg <= timedelta(hours=1):
            results.append({"place": place, "type": "meal_place"})

        else:
            results.append({"place": place, "type": "unknown"})

    return results