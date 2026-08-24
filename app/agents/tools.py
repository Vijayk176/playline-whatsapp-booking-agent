import json
import logging
from datetime import datetime, date, time
from sqlalchemy.orm import Session
from app.services import booking_service as bs

logger = logging.getLogger("tools")

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_gaming_options",
            "description": "Get the list of active gaming options with their hourly prices. Use for 'what games do you have' or 'price' questions.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check if a gaming option is available on a given date/time/duration before booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gaming_option_name": {"type": "string", "description": "Name of the gaming option, e.g. PS5"},
                    "booking_date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "start_time": {"type": "string", "description": "Start time in HH:MM 24-hour format"},
                    "duration_hours": {"type": "number", "description": "Duration in hours, can be decimal e.g. 1.5"},
                },
                "required": ["gaming_option_name", "booking_date", "start_time", "duration_hours"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "Create a confirmed booking. Only call this AFTER the customer has explicitly confirmed (said yes) to the booking summary including price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "gaming_option_name": {"type": "string"},
                    "booking_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "start_time": {"type": "string", "description": "HH:MM 24-hour"},
                    "duration_hours": {"type": "number"},
                },
                "required": ["customer_name", "gaming_option_name", "booking_date", "start_time", "duration_hours"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_bookings",
            "description": "Get the customer's active (upcoming, non-cancelled) bookings using their WhatsApp phone number.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancel a booking by its booking reference. Only call after the customer confirms which booking to cancel.",
            "parameters": {
                "type": "object",
                "properties": {"booking_ref": {"type": "string"}},
                "required": ["booking_ref"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_booking",
            "description": "Reschedule an existing booking to a new date/time. Only call after the customer confirms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_ref": {"type": "string"},
                    "new_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "new_start_time": {"type": "string", "description": "HH:MM 24-hour"},
                },
                "required": ["booking_ref", "new_date", "new_start_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_business_information",
            "description": "Get business info: address, phone, opening/closing hours, social links. Use for location/timing questions.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_to_human",
            "description": "Escalate to a human staff member. Use when the customer asks for a human/agent/owner/manager, or the request is too complex.",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string", "description": "Short summary of why escalating"}},
                "required": ["reason"],
            },
        },
    },
]


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _parse_time(s: str) -> time:
    s = s.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized time format: {s}")


class ToolExecutor:
    """Executes tool calls against the real database. The AI never touches the DB directly."""

    def __init__(self, db: Session, phone: str):
        self.db = db
        self.phone = phone

    def execute(self, name: str, arguments: dict) -> dict:
        try:
            method = getattr(self, f"_{name}")
        except AttributeError:
            return {"error": f"Unknown tool: {name}"}
        try:
            return method(**arguments)
        except bs.BookingError as e:
            return {"error": e.message, "suggestions": e.suggestions}
        except Exception as e:  # noqa: BLE001
            return {"error": f"Something went wrong: {str(e)}"}

    def _get_gaming_options(self):
        options = bs.get_active_gaming_options(self.db)
        return {
            "options": [
                {"name": o.name, "price_per_hour": o.price_per_hour, "description": o.description, "capacity": o.capacity}
                for o in options
            ]
        }

    def _check_availability(self, gaming_option_name, booking_date, start_time, duration_hours):
        option = bs.find_gaming_option_by_name(self.db, gaming_option_name)
        if not option:
            return {"error": f"'{gaming_option_name}' is not a valid gaming option."}
        d = _parse_date(booking_date)
        t = _parse_time(start_time)
        available, conflict = bs.check_availability(self.db, option.id, d, t, float(duration_hours))
        if available:
            price = bs.calculate_price(option, float(duration_hours))
            return {"available": True, "price": price, "gaming_option": option.name}
        suggestions = bs.suggest_nearby_times(self.db, option.id, d, float(duration_hours), t)
        return {"available": False, "gaming_option": option.name, "suggested_times": suggestions}

    def _create_booking(self, customer_name, gaming_option_name, booking_date, start_time, duration_hours):
        option = bs.find_gaming_option_by_name(self.db, gaming_option_name)
        if not option:
            return {"error": f"'{gaming_option_name}' is not a valid gaming option."}
        d = _parse_date(booking_date)
        t = _parse_time(start_time)
        booking = bs.create_booking(self.db, customer_name, self.phone, option.id, d, t, float(duration_hours))
        return {
            "success": True,
            "booking_ref": booking.booking_ref,
            "gaming_option": option.name,
            "date": booking.booking_date.strftime("%d %B %Y"),
            "start_time": booking.start_time.strftime("%I:%M %p"),
            "end_time": booking.end_time.strftime("%I:%M %p"),
            "duration_hours": booking.duration_hours,
            "price": booking.price,
        }

    def _get_customer_bookings(self):
        bookings = bs.get_customer_active_bookings(self.db, self.phone)
        return {
            "bookings": [
                {
                    "booking_ref": b.booking_ref,
                    "gaming_option": b.gaming_option.name,
                    "date": b.booking_date.strftime("%d %B %Y"),
                    "start_time": b.start_time.strftime("%I:%M %p"),
                    "status": b.status.value if hasattr(b.status, "value") else b.status,
                }
                for b in bookings
            ]
        }

    def _cancel_booking(self, booking_ref):
        booking = bs.cancel_booking(self.db, booking_ref, self.phone)
        return {"success": True, "booking_ref": booking.booking_ref, "status": booking.status.value}

    def _reschedule_booking(self, booking_ref, new_date, new_start_time):
        d = _parse_date(new_date)
        t = _parse_time(new_start_time)
        booking = bs.reschedule_booking(self.db, booking_ref, self.phone, d, t)
        return {
            "success": True,
            "booking_ref": booking.booking_ref,
            "new_date": booking.booking_date.strftime("%d %B %Y"),
            "new_start_time": booking.start_time.strftime("%I:%M %p"),
        }

    def _get_business_information(self):
        biz = bs.get_or_create_business_settings(self.db)
        return {
            "business_name": biz.business_name,
            "address": biz.address,
            "phone": biz.phone,
            "opening_time": biz.opening_time.strftime("%I:%M %p"),
            "closing_time": biz.closing_time.strftime("%I:%M %p"),
            "weekly_closed_day": biz.weekly_closed_day,
            "google_maps_link": biz.google_maps_link,
            "instagram_link": biz.instagram_link,
            "facebook_link": biz.facebook_link,
            "description": biz.general_description,
        }

    def _handoff_to_human(self, reason):
        from app.models.models import SupportRequest
        from app.services.whatsapp import send_message_sync

        customer = bs.get_or_create_customer(self.db, self.phone)
        req = SupportRequest(customer_phone=self.phone, customer_name=customer.name or "", message=reason)
        self.db.add(req)
        self.db.commit()

        biz = bs.get_or_create_business_settings(self.db)
        notified = False
        if biz.owner_notification_phone:
            display_name = customer.name or self.phone
            alert_text = (
                f"🔔 PlayLine handoff request\n\n"
                f"Customer: {display_name}\n"
                f"Phone: {self.phone}\n"
                f"Reason: {reason}\n\n"
                f"Reply to them directly on WhatsApp, or open /admin/support."
            )
            notified = send_message_sync(biz.owner_notification_phone, alert_text)
            if not notified:
                logger.warning("Owner notification failed to send for support request id=%s", req.id)
        else:
            logger.info("owner_notification_phone not configured; handoff only recorded in dashboard (id=%s)", req.id)

        return {"success": True, "message": "A staff member will contact you shortly.", "owner_notified": notified}
