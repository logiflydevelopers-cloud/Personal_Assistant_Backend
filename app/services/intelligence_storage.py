def save_wakeup(db, user_id, timestamp):
    db.execute("""
        INSERT INTO user_daily_summary (user_id, date, wake_time)
        VALUES (:user_id, :date, :wake_time)
        ON CONFLICT (user_id, date)
        DO UPDATE SET wake_time = :wake_time
    """, {
        "user_id": user_id,
        "date": timestamp.date(),
        "wake_time": timestamp
    })
    db.commit()

def save_sleep(db, user_id, timestamp):
    db.execute("""
        INSERT INTO user_daily_summary (user_id, date, sleep_time)
        VALUES (:user_id, :date, :sleep_time)
        ON CONFLICT (user_id, date)
        DO UPDATE SET sleep_time = :sleep_time
    """, {
        "user_id": user_id,
        "date": timestamp.date(),
        "sleep_time": timestamp
    })
    db.commit()

def save_screen_behaviour(db, user_id, result, date):
    db.execute("""
        INSERT INTO user_daily_summary (user_id, date, total_screen_time, behaviour_type)
        VALUES (:user_id, :date, :screen_time, :behaviour)
        ON CONFLICT (user_id, date)
        DO UPDATE SET
            total_screen_time = :screen_time,
            behaviour_type = :behaviour
    """, {
        "user_id": user_id,
        "date": date,
        "screen_time": result["total_screen_time_seconds"],
        "behaviour": result["behaviour"]
    })
    db.commit()

def save_meals(db, user_id, meals):
    for meal in meals:
        db.execute("""
            INSERT INTO user_meals (user_id, meal_type, time, confidence)
            VALUES (:user_id, :meal_type, :time, :confidence)
        """, {
            "user_id": user_id,
            "meal_type": meal["meal_type"],
            "time": meal["time"],
            "confidence": meal["confidence"]
        })
    db.commit()