from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.models import Customer, Booking
from app.services.auth_service import get_current_admin

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("")
def list_customers(db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    customers = db.query(Customer).order_by(Customer.created_at.desc()).all()
    result = []
    for c in customers:
        total = db.query(func.count(Booking.id)).filter(Booking.customer_id == c.id).scalar()
        last_booking = (
            db.query(Booking)
            .filter(Booking.customer_id == c.id)
            .order_by(Booking.booking_date.desc())
            .first()
        )
        result.append({
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "total_bookings": total,
            "last_booking_date": last_booking.booking_date.isoformat() if last_booking else None,
            "last_booking_status": last_booking.status.value if last_booking else None,
        })
    return result
