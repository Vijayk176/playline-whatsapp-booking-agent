from datetime import date, time, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.models import Booking, GamingOption, Customer, BusinessSetting, BookingStatus
from app.utils.timezone import now_local, today_local


class BookingError(Exception):
    def __init__(self, message: str, suggestions: Optional[list] = None):
        self.message = message
        self.suggestions = suggestions or []
        super().__init__(message)


def get_or_create_business_settings(db: Session) -> BusinessSetting:
    settings_row = db.query(BusinessSetting).first()
    if not settings_row:
        settings_row = BusinessSetting()
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
    return settings_row


def get_or_create_customer(db: Session, phone: str, name: Optional[str] = None) -> Customer:
    customer = db.query(Customer).filter(Customer.phone == phone).first()
    if not customer:
        customer = Customer(phone=phone, name=name)
        db.add(customer)
        db.commit()
        db.refresh(customer)
    elif name and not customer.name:
        customer.name = name
        db.commit()
        db.refresh(customer)
    return customer


def get_active_gaming_options(db: Session):
    return db.query(GamingOption).filter(GamingOption.active == True).all()  # noqa: E712


def find_gaming_option_by_name(db: Session, name: str) -> Optional[GamingOption]:
    name = name.strip().lower()
    options = get_active_gaming_options(db)
    for opt in options:
        if opt.name.lower() == name:
            return opt
    for opt in options:
        if name in opt.name.lower() or opt.name.lower() in name:
            return opt
    return None


def _end_time(start: time, duration_hours: float) -> time:
    dt = datetime.combine(date.today(), start) + timedelta(hours=duration_hours)
    return dt.time()


def validate_business_hours(db: Session, booking_date: date, start: time, end: time):
    biz = get_or_create_business_settings(db)
    open_t, close_t = biz.opening_time, biz.closing_time
    # Overnight hours (e.g. 12:00 -> 00:00 next day) handled as close_t <= open_t meaning "until midnight or later"
    if close_t <= open_t:
        # business spans midnight; treat close_t as end-of-day boundary unless it's genuinely early morning
        if start < open_t and start > close_t:
            raise BookingError(f"Booking time must be within business hours ({open_t.strftime('%I:%M %p')} - {close_t.strftime('%I:%M %p')}).")
    else:
        if start < open_t or start >= close_t:
            raise BookingError(f"Booking time must be within business hours ({open_t.strftime('%I:%M %p')} - {close_t.strftime('%I:%M %p')}).")
        if end > close_t:
            raise BookingError(f"Booking would end after closing time ({close_t.strftime('%I:%M %p')}). Please choose an earlier start time or shorter duration.")

    weekday_name = booking_date.strftime("%A")
    if biz.weekly_closed_day and biz.weekly_closed_day != "None" and biz.weekly_closed_day == weekday_name:
        raise BookingError(f"We are closed on {weekday_name}s. Please choose a different date.")


def validate_not_in_past(booking_date: date, start: time):
    booking_dt = datetime.combine(booking_date, start)
    if booking_dt < now_local().replace(tzinfo=None):
        raise BookingError("This time is in the past. Please choose a future date/time.")


def check_availability(db: Session, gaming_option_id: int, booking_date: date,
                        start: time, duration_hours: float, exclude_booking_id: Optional[int] = None):
    """Returns (available: bool, conflicting_booking or None)."""
    end = _end_time(start, duration_hours)
    query = db.query(Booking).filter(
        Booking.gaming_option_id == gaming_option_id,
        Booking.booking_date == booking_date,
        Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed]),
    )
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)

    for existing in query.all():
        existing_start = existing.start_time
        existing_end = existing.end_time
        # Overlap if start < existing_end and end > existing_start
        if start < existing_end and end > existing_start:
            return False, existing
    return True, None


def suggest_nearby_times(db: Session, gaming_option_id: int, booking_date: date,
                          duration_hours: float, desired_start: time) -> list:
    biz = get_or_create_business_settings(db)
    open_t, close_t = biz.opening_time, biz.closing_time
    suggestions = []
    slot = datetime.combine(booking_date, open_t)
    close_dt = datetime.combine(booking_date, close_t) if close_t > open_t else datetime.combine(booking_date + timedelta(days=1), close_t)
    step = timedelta(minutes=30)
    while slot + timedelta(hours=duration_hours) <= close_dt and len(suggestions) < 6:
        candidate_start = slot.time()
        available, _ = check_availability(db, gaming_option_id, booking_date, candidate_start, duration_hours)
        if available:
            suggestions.append(candidate_start.strftime("%I:%M %p").lstrip("0"))
        slot += step
    return suggestions


def calculate_price(gaming_option: GamingOption, duration_hours: float) -> float:
    return round(gaming_option.price_per_hour * duration_hours, 2)


def generate_booking_ref(db: Session, booking_date: date) -> str:
    prefix = f"ODG-{booking_date.strftime('%Y%m%d')}"
    count_today = db.query(Booking).filter(Booking.booking_ref.like(f"{prefix}-%")).count()
    seq = str(count_today + 1).zfill(4)
    ref = f"{prefix}-{seq}"
    while db.query(Booking).filter(Booking.booking_ref == ref).first():
        count_today += 1
        seq = str(count_today + 1).zfill(4)
        ref = f"{prefix}-{seq}"
    return ref


def create_booking(db: Session, customer_name: str, phone: str, gaming_option_id: int,
                    booking_date: date, start: time, duration_hours: float, notes: str = "") -> Booking:
    if duration_hours <= 0 or duration_hours > 12:
        raise BookingError("Duration must be between 0 and 12 hours.")

    gaming_option = db.query(GamingOption).filter(
        GamingOption.id == gaming_option_id, GamingOption.active == True  # noqa: E712
    ).first()
    if not gaming_option:
        raise BookingError("That gaming option is not available.")

    validate_not_in_past(booking_date, start)
    end = _end_time(start, duration_hours)
    validate_business_hours(db, booking_date, start, end)

    available, conflict = check_availability(db, gaming_option_id, booking_date, start, duration_hours)
    if not available:
        suggestions = suggest_nearby_times(db, gaming_option_id, booking_date, duration_hours, start)
        raise BookingError(
            f"{gaming_option.name} is already booked at that time "
            f"({conflict.start_time.strftime('%I:%M %p')} - {conflict.end_time.strftime('%I:%M %p')}).",
            suggestions=suggestions,
        )

    customer = get_or_create_customer(db, phone, customer_name)
    price = calculate_price(gaming_option, duration_hours)
    ref = generate_booking_ref(db, booking_date)

    booking = Booking(
        booking_ref=ref,
        customer_id=customer.id,
        gaming_option_id=gaming_option_id,
        customer_name=customer_name,
        phone=phone,
        booking_date=booking_date,
        start_time=start,
        duration_hours=duration_hours,
        end_time=end,
        price=price,
        status=BookingStatus.confirmed,
        notes=notes,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_customer_active_bookings(db: Session, phone: str):
    return db.query(Booking).filter(
        Booking.phone == phone,
        Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed]),
        Booking.booking_date >= today_local(),
    ).order_by(Booking.booking_date, Booking.start_time).all()


def cancel_booking(db: Session, booking_ref: str, phone: str) -> Booking:
    booking = db.query(Booking).filter(
        Booking.booking_ref == booking_ref, Booking.phone == phone
    ).first()
    if not booking:
        raise BookingError("Booking not found for this phone number.")
    if booking.status == BookingStatus.cancelled:
        raise BookingError("This booking is already cancelled.")
    booking.status = BookingStatus.cancelled
    db.commit()
    db.refresh(booking)
    return booking


def reschedule_booking(db: Session, booking_ref: str, phone: str,
                        new_date: date, new_start: time) -> Booking:
    booking = db.query(Booking).filter(
        Booking.booking_ref == booking_ref, Booking.phone == phone
    ).first()
    if not booking:
        raise BookingError("Booking not found for this phone number.")
    if booking.status not in (BookingStatus.pending, BookingStatus.confirmed):
        raise BookingError("This booking cannot be rescheduled.")

    validate_not_in_past(new_date, new_start)
    new_end = _end_time(new_start, booking.duration_hours)
    validate_business_hours(db, new_date, new_start, new_end)

    available, conflict = check_availability(
        db, booking.gaming_option_id, new_date, new_start, booking.duration_hours,
        exclude_booking_id=booking.id,
    )
    if not available:
        suggestions = suggest_nearby_times(db, booking.gaming_option_id, new_date, booking.duration_hours, new_start)
        raise BookingError(
            f"That time is not available "
            f"(conflicts with {conflict.start_time.strftime('%I:%M %p')} - {conflict.end_time.strftime('%I:%M %p')}).",
            suggestions=suggestions,
        )

    booking.booking_date = new_date
    booking.start_time = new_start
    booking.end_time = new_end
    db.commit()
    db.refresh(booking)
    return booking
