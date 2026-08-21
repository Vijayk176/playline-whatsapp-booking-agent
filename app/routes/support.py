from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import SupportRequest, SupportStatus
from app.schemas.schemas import SupportRequestOut, SupportStatusUpdate
from app.services.auth_service import get_current_admin

router = APIRouter(prefix="/api/support", tags=["support"])


@router.get("", response_model=list[SupportRequestOut])
def list_support_requests(db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    return db.query(SupportRequest).order_by(SupportRequest.created_at.desc()).all()


@router.put("/{request_id}", response_model=SupportRequestOut)
def update_support_status(request_id: int, data: SupportStatusUpdate, db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    req = db.query(SupportRequest).filter(SupportRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Support request not found")
    if data.status not in [s.value for s in SupportStatus]:
        raise HTTPException(status_code=400, detail="Invalid status")
    req.status = data.status
    db.commit()
    db.refresh(req)
    return req
