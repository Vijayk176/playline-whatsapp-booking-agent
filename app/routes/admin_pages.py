from datetime import date
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.models import Booking, GamingOption, SupportRequest, BookingStatus, SupportStatus
from app.utils.security import decode_access_token
from app.services import booking_service as bs

router = APIRouter(prefix="/admin", tags=["admin-pages"])
templates = Jinja2Templates(directory="app/templates")


def _require_admin(request: Request):
    token = request.cookies.get("session_token")
    username = decode_access_token(token) if token else None
    return username


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    admin = _require_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)

    today = date.today()
    stats = {
        "total_bookings": db.query(func.count(Booking.id)).scalar(),
        "today_bookings": db.query(func.count(Booking.id)).filter(Booking.booking_date == today).scalar(),
        "pending_bookings": db.query(func.count(Booking.id)).filter(Booking.status == BookingStatus.pending).scalar(),
        "confirmed_bookings": db.query(func.count(Booking.id)).filter(Booking.status == BookingStatus.confirmed).scalar(),
        "cancelled_bookings": db.query(func.count(Booking.id)).filter(Booking.status == BookingStatus.cancelled).scalar(),
        "revenue": db.query(func.coalesce(func.sum(Booking.price), 0)).filter(
            Booking.status.in_([BookingStatus.confirmed, BookingStatus.completed])
        ).scalar(),
        "active_games": db.query(func.count(GamingOption.id)).filter(GamingOption.active == True).scalar(),  # noqa: E712
        "open_support": db.query(func.count(SupportRequest.id)).filter(SupportRequest.status == SupportStatus.open).scalar(),
    }
    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats, "admin": admin, "active_page": "dashboard"})


@router.get("/bookings", response_class=HTMLResponse)
def bookings_page(request: Request, db: Session = Depends(get_db)):
    admin = _require_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)
    bookings = db.query(Booking).order_by(Booking.booking_date.desc(), Booking.start_time.desc()).limit(200).all()
    return templates.TemplateResponse("bookings.html", {"request": request, "bookings": bookings, "admin": admin, "active_page": "bookings"})


@router.get("/games", response_class=HTMLResponse)
def games_page(request: Request, db: Session = Depends(get_db)):
    admin = _require_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)
    games = db.query(GamingOption).order_by(GamingOption.id).all()
    return templates.TemplateResponse("games.html", {"request": request, "games": games, "admin": admin, "active_page": "games"})


@router.get("/customers", response_class=HTMLResponse)
def customers_page(request: Request, db: Session = Depends(get_db)):
    admin = _require_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)
    from app.models.models import Customer
    customers = db.query(Customer).order_by(Customer.created_at.desc()).all()
    return templates.TemplateResponse("customers.html", {"request": request, "customers": customers, "admin": admin, "active_page": "customers"})


@router.get("/support", response_class=HTMLResponse)
def support_page(request: Request, db: Session = Depends(get_db)):
    admin = _require_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)
    requests_list = db.query(SupportRequest).order_by(SupportRequest.created_at.desc()).all()
    return templates.TemplateResponse("support.html", {"request": request, "requests": requests_list, "admin": admin, "active_page": "support"})


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    admin = _require_admin(request)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=303)
    biz = bs.get_or_create_business_settings(db)
    return templates.TemplateResponse("settings.html", {"request": request, "biz": biz, "admin": admin, "active_page": "settings"})
