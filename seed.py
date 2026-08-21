"""
Seed the database with SAMPLE demo data for PlayLine (WhatsApp AI Booking Agent).
Run: python seed.py
IMPORTANT: Replace these sample values with the real gaming zone's data via the admin dashboard
(Settings + Gaming Options pages) before going live with a client.
"""
from datetime import time
from app.database import init_db, SessionLocal
from app.models.models import GamingOption, BusinessSetting
from app.services.auth_service import ensure_default_admin

SAMPLE_GAMES = [
    {"name": "PS5", "description": "SAMPLE - PlayStation 5 with 2 controllers", "price_per_hour": 500, "capacity": 4},
    {"name": "PS4", "description": "SAMPLE - PlayStation 4 with 2 controllers", "price_per_hour": 400, "capacity": 4},
    {"name": "Gaming PC", "description": "SAMPLE - High-end gaming PC", "price_per_hour": 300, "capacity": 1},
    {"name": "Xbox", "description": "SAMPLE - Xbox Series X", "price_per_hour": 400, "capacity": 4},
    {"name": "Racing Simulator", "description": "SAMPLE - Racing rig with force feedback wheel", "price_per_hour": 800, "capacity": 1},
]


def seed():
    init_db()
    db = SessionLocal()
    try:
        ensure_default_admin(db)

        if db.query(GamingOption).count() == 0:
            for g in SAMPLE_GAMES:
                db.add(GamingOption(**g))
            print(f"Seeded {len(SAMPLE_GAMES)} SAMPLE gaming options. Replace prices/names in admin dashboard.")
        else:
            print("Gaming options already exist, skipping.")

        if db.query(BusinessSetting).count() == 0:
            db.add(BusinessSetting(
                business_name="Demo Gaming Zone (SAMPLE - rename in Settings)",
                address="SAMPLE ADDRESS - replace with the client's real address",
                phone="0300-0000000 (SAMPLE - replace with real number)",
                whatsapp_number="0300-0000000 (SAMPLE - replace with real number)",
                opening_time=time(12, 0),
                closing_time=time(23, 59),
                weekly_closed_day="None",
                google_maps_link="https://maps.google.com/?q=YOUR+BUSINESS (SAMPLE)",
                instagram_link="https://instagram.com/SAMPLE",
                facebook_link="https://facebook.com/SAMPLE",
                general_description="SAMPLE DESCRIPTION - replace with a description of this gaming zone.",
            ))
            print("Seeded SAMPLE business settings. Replace via /admin/settings.")
        else:
            print("Business settings already exist, skipping.")

        db.commit()
        print("Seeding complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
