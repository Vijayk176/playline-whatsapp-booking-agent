from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from app.database import get_db
from app.models.models import Booking, BookingStatus
from app.schemas.schemas import BookingIn, BookingOut, BookingStatusUpdate, PaymentStatusUpdate
from app.services import booking_service as bs
from app.services.auth_service import get_current_admin

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut)
def create_booking_api(data: BookingIn, db: Session = Depends(get_db)):
    try:
        booking = bs.create_booking(
            db, data.customer_name, data.phone, data.gaming_option_id,
            data.booking_date, data.start_time, data.duration_hours, data.notes,
        )
        return booking
    except bs.BookingError as e:
        raise HTTPException(status_code=400, detail={"message": e.message, "suggestions": e.suggestions})


@router.get("", response_model=list[BookingOut])
def list_bookings(
    status_filter: Optional[str] = Query(None, alias="status"),
    date_filter: Optional[date] = Query(None, alias="date"),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    q = db.query(Booking)
    if status_filter:
        q = q.filter(Booking.status == status_filter)
    if date_filter:
        q = q.filter(Booking.booking_date == date_filter)
    if search:
        like = f"%{search}%"
        q = q.filter((Booking.customer_name.like(like)) | (Booking.phone.like(like)) | (Booking.booking_ref.like(like)))
    return q.order_by(Booking.booking_date.desc(), Booking.start_time.desc()).limit(200).all()


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.put("/{booking_id}", response_model=BookingOut)
def update_booking_status(booking_id: int, data: BookingStatusUpdate, db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if data.status not in [s.value for s in BookingStatus]:
        raise HTTPException(status_code=400, detail="Invalid status")
    booking.status = data.status
    db.commit()
    db.refresh(booking)
    return booking


@router.put("/{booking_id}/payment", response_model=BookingOut)
def update_payment_status(booking_id: int, data: PaymentStatusUpdate, db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.payment_status = data.payment_status
    db.commit()
    db.refresh(booking)
    return booking


@router.delete("/{booking_id}")
def delete_booking(booking_id: int, db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()
    return {"status": "deleted"}
