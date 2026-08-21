import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import init_db, SessionLocal
from app.utils.rate_limit import RateLimitMiddleware
from app.services.auth_service import ensure_default_admin
from app.routes import webhook, bookings, games, customers, support, settings as settings_routes
from app.routes import admin_auth, admin_pages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

app = FastAPI(title="PlayLine WhatsApp Booking Agent")

app.add_middleware(RateLimitMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(webhook.router)
app.include_router(bookings.router)
app.include_router(games.router)
app.include_router(customers.router)
app.include_router(support.router)
app.include_router(settings_routes.router)
app.include_router(admin_auth.router)
app.include_router(admin_pages.router)


@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()
    logger.info("PlayLine WhatsApp Booking Agent started")


@app.get("/")
def root():
    return {"status": "ok", "service": "PlayLine WhatsApp Booking Agent"}


@app.get("/health")
def health():
    return {"status": "healthy"}
