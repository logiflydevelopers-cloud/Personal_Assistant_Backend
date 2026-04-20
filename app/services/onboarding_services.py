from sqlalchemy.orm import Session
from app.models.onboarding import User, Habit, Routine

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

    # Create routine
    routine = Routine(
        user_id=user.id,
        wake_time=data.wake_time,
        sleep_time=data.sleep_time,
        active_hours=data.active_hours,
        break_hours=data.break_hours
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

    db.commit()

    return {"message": "Onboarding completed", "user_id": user.user_id}