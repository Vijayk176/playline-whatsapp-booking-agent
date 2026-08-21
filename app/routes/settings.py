from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.schemas import BusinessSettingIn
from app.services import booking_service as bs
from app.services.auth_service import get_current_admin

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings(db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    return bs.get_or_create_business_settings(db)


@router.put("")
def update_settings(data: BusinessSettingIn, db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    settings_row = bs.get_or_create_business_settings(db)
    for k, v in data.model_dump().items():
        setattr(settings_row, k, v)
    db.commit()
    db.refresh(settings_row)
    return settings_row
