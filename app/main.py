from fastapi import FastAPI
from app.db.base import Base
from app.db.session import engine

Base.metadata.create_all(bind=engine)

from app.api.onboarding import router as onboarding_router
from app.api.user_events import router as user_events_router

app = FastAPI(title="AI Assistant Backend")

# include routes
app.include_router(onboarding_router, prefix="/api")
app.include_router(user_events_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Backend is running 🚀"}