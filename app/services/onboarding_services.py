from sqlalchemy.orm import Session
from app.models.onboarding import User, Habit, Routine
from datetime import datetime


# helper function
def calculate_hobby_hours(wake_time, sleep_time, active_hours, break_hours):
    fmt = "%H:%M"

    wake = datetime.strptime(str(wake_time), fmt)
    sleep = datetime.strptime(str(sleep_time), fmt)

    # handle midnight case
    if sleep < wake:
        sleep = sleep.replace(day=sleep.day + 1)

    awake_hours = (sleep - wake).total_seconds() / 3600

    hobby_hours = awake_hours - active_hours - break_hours

    return round(hobby_hours, 2)


def create_onboarding(data, db: Session):
    # Create user
    user = User(
        name=data.name,
        age_group=data.age_group,
        occupation=data.occupation
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # calculate hobby hours BEFORE saving
    hobby_hours = calculate_hobby_hours(
        data.wake_time,
        data.sleep_time,
        data.active_hours,
        data.break_hours
    )

    # Create routine 
    routine = Routine(
        user_id=user.id,
        wake_time=data.wake_time,
        sleep_time=data.sleep_time,
        active_hours=data.active_hours,
        break_hours=data.break_hours,
        hobby_hours=hobby_hours   
    )
    db.add(routine)

    # Create habits
    for h in data.habits:
        habit = Habit(
            user_id=user.id,
            name=h.name,
            frequency=h.frequency,
            preferred_time=h.preferred_time
        )
        db.add(habit)

    # single commit
    db.commit()

    return {
        "message": "Onboarding completed",
        "user_id": user.user_id
    }