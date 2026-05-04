from sqlalchemy import text
from datetime import timedelta

def save_wakeup(db, user_id, timestamp):

    db.execute(text("""
        INSERT INTO user_daily_summary (user_id, date, wake_time)
        VALUES (:user_id, :date, :wake_time)
        ON CONFLICT (user_id, date)
        DO UPDATE SET wake_time = :wake_time
    """), {
        "user_id": user_id,
        "date": timestamp.date(),
        "wake_time": timestamp
    })

    db.commit()

def save_sleep(db, user_id, timestamp):

    sleep_date = timestamp.date()
    if timestamp.hour <= 3:
        sleep_date = sleep_date - timedelta(days=1)

    db.execute(text("""
        INSERT INTO user_daily_summary (user_id, date, sleep_time)
        VALUES (:user_id, :date, :sleep_time)
        ON CONFLICT (user_id, date)
        DO UPDATE SET sleep_time = :sleep_time
    """), {
        "user_id": user_id,
        "date": sleep_date,
        "sleep_time": timestamp
    })

    db.commit()


def save_screen_behaviour(db, user_id, result, date):

    print("\n===== SAVING SCREEN BEHAVIOUR =====")
    print(result)

    db.execute(text("""
        INSERT INTO user_daily_summary (user_id, date, total_screen_time, behaviour_type)
        VALUES (:user_id, :date, :screen_time, :behaviour)
        ON CONFLICT (user_id, date)
        DO UPDATE SET
            total_screen_time = :screen_time,
            behaviour_type = :behaviour
    """), {
        "user_id": user_id,
        "date": date,
        "screen_time": result.get("total_screen_time") or result.get("total_screen_time_seconds"),
        "behaviour": result["behaviour"]
    })

    db.commit()

    print("SAVED SUCCESSFULLY\n")

def save_meals(db, user_id, meals):

    print("\n===== SAVE MEALS START =====")

    for meal in meals:
        try:
            print(f"Processing meal: {meal}")

            # Prevent duplicate (within 30 mins)
            existing = db.execute(text("""
                SELECT time FROM user_meals
                WHERE user_id = :user_id
                AND meal_type = :meal_type
                AND ABS(EXTRACT(EPOCH FROM (time - :time))) < 1800
            """), {
                "user_id": user_id,
                "meal_type": meal["meal_type"],
                "time": meal["time"]
            }).fetchone()

            print(f"Existing meal check: {existing}")

            if existing:
                print("Duplicate meal detected → skipping")
                continue

            # Insert meal
            db.execute(text("""
                INSERT INTO user_meals (user_id, meal_type, time, confidence)
                VALUES (:user_id, :meal_type, :time, :confidence)
            """), {
                "user_id": user_id,
                "meal_type": meal["meal_type"],
                "time": meal["time"],
                "confidence": meal["confidence"]
            })

            print("Meal saved successfully")

        except Exception as e:
            print(f"Error saving meal: {e}")
            db.rollback()

    db.commit()

    print("===== SAVE MEALS END =====\n")


def save_place_visits(db, user_id, stays):

    print("\n===== SAVE PLACE VISITS START =====")

    for stay in stays:
        try:
            print(f"Processing stay: {stay}")

            # Extract values correctly
            start_ = stay["start_time"]
            end_ = stay["end_time"]
            duration = stay["duration"]
            lat = stay["lat"]
            lon = stay["lon"]

            # Prevent duplicate visits
            existing = db.execute(text("""
                SELECT id FROM user_place_visits
                WHERE user_id = :user_id
                AND ABS(EXTRACT(EPOCH FROM (start_time - :start_time))) < 300
            """), {
                "user_id": user_id,
                "start_time": start_
            }).fetchone()

            if existing:
                print("Duplicate visit → skipping")
                continue

            # OPTIONAL: find existing place_id
            place = db.execute(text("""
                SELECT id FROM user_places
                WHERE user_id = :user_id
                AND ABS(lat - :lat) < 0.001
                AND ABS(lon - :lon) < 0.001
            """), {
                "user_id": user_id,
                "lat": lat,
                "lon": lon
            }).fetchone()

            place_id = place[0] if place else None

            db.execute(text("""
                INSERT INTO user_place_visits (
                    user_id, place_id, start_time, end_time, duration, lat, lon
                )
                VALUES (
                    :user_id, :place_id, :start_time, :end_time, :duration, :lat, :lon
                )
            """), {
                "user_id": user_id,
                "place_id": place_id,
                "start_time": start_,
                "end_time": end_,
                "duration": int(duration.total_seconds()),
                "lat": lat,
                "lon": lon
            })

            print("Visit saved")

        except Exception as e:
            print(f"Error saving visit: {e}")
            db.rollback()

    db.commit()

    print("===== SAVE PLACE VISITS END =====\n")


def save_places(db, user_id, places):

    print("\n===== SAVE PLACES START =====")

    for place in places:
        try:
            lat, lon = place["place"]
            place_type = place["type"]

            print(f"Processing place: {place}")

            existing = db.execute(text("""
                SELECT id FROM user_places
                WHERE user_id = :user_id
                AND ABS(lat - :lat) < 0.001
                AND ABS(lon - :lon) < 0.001
            """), {
                "user_id": user_id,
                "lat": lat,
                "lon": lon
            }).fetchone()

            if existing:
                db.execute(text("""
                    UPDATE user_places
                    SET place_type = :type,
                        updated_at = NOW()
                    WHERE id = :id
                """), {
                    "id": existing[0],
                    "type": place_type
                })

                print("Updated existing place")

            else:
                db.execute(text("""
                    INSERT INTO user_places (user_id, lat, lon, place_type)
                    VALUES (:user_id, :lat, :lon, :type)
                """), {
                    "user_id": user_id,
                    "lat": lat,   
                    "lon": lon,
                    "type": place_type
                })

                print("Inserted new place")

        except Exception as e:
            print(f"Error saving place: {e}")
            db.rollback()

    db.commit()

    print("===== SAVE PLACES END =====\n")