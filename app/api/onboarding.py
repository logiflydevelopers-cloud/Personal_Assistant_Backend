from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.onboarding_schema import Onboarding
from app.services.onboarding_services import create_onboarding
from app.db.session import get_db

router = APIRouter()

@router.post("/onboarding")
def onboarding(data: Onboarding, db: Session = Depends(get_db)):
    return create_onboarding(data, db)
