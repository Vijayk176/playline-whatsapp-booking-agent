import re
from app.agents.base import BaseAgent

KEYWORDS = {
    "price": ["price", "rate", "kitna", "kitnay", "paisay", "paisa", "charges"],
    "location": ["location", "address", "kidhar", "kahan", "where"],
    "timing": ["timing", "time open", "khulte", "band", "close", "hours"],
    "booking": ["book", "booking", "reserve", "chahiye", "karna hai"],
    "cancel": ["cancel", "cancel karo", "cancel kardain"],
    "human": ["human", "agent", "owner", "manager", "staff", "talk to someone", "call me"],
    "games": ["game", "games", "options", "ps5", "ps4", "xbox", "pc", "simulator"],
}


def _match_intent(text: str) -> str:
    text_lower = text.lower()
    for intent, words in KEYWORDS.items():
        for w in words:
            if w in text_lower:
                return intent
    return "unknown"


class FallbackAgent(BaseAgent):
    """Deterministic, keyword-based responses. Used when the AI provider is down.
    Does not use tool-calling; relies on the caller (conversation service) for
    complex flows. This mainly handles simple FAQ-style intents."""

    async def respond(self, phone: str, history: list, tool_executor) -> str:
        last_user_msg = ""
        for m in reversed(history):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        intent = _match_intent(last_user_msg)

        if intent == "price" or intent == "games":
            result = tool_executor.execute("get_gaming_options", {})
            options = result.get("options", [])
            if not options:
                return "Sorry, no gaming options are configured right now. Please contact staff."
            lines = [f"🎮 {o['name']} — Rs. {o['price_per_hour']:.0f}/hour" for o in options]
            return "Our current gaming options:\n\n" + "\n".join(lines) + "\n\nWhich one would you like to book?"

        if intent == "location":
            info = tool_executor.execute("get_business_information", {})
            return f"📍 {info.get('address', '')}\n\nMap: {info.get('google_maps_link', '')}"

        if intent == "timing":
            info = tool_executor.execute("get_business_information", {})
            return f"🕐 We're open {info.get('opening_time')} - {info.get('closing_time')} daily."

        if intent == "human":
            tool_executor.execute("handoff_to_human", {"reason": f"Fallback mode escalation: {last_user_msg}"})
            return "I've notified our staff and they'll reach out to you shortly. 🙏"

        if intent == "cancel":
            result = tool_executor.execute("get_customer_bookings", {})
            bookings = result.get("bookings", [])
            if not bookings:
                return "You don't have any active bookings to cancel."
            lines = [f"{i+1}. {b['booking_ref']} — {b['gaming_option']} — {b['date']} {b['start_time']}" for i, b in enumerate(bookings)]
            return "Which booking would you like to cancel? Please reply with the booking ID:\n\n" + "\n".join(lines)

        if intent == "booking":
            return (
                "Sure! 🎮 Our AI booking assistant is temporarily limited, but I can still help.\n\n"
                "Please tell me: gaming option, date, start time, and duration (e.g. 'PS5, tomorrow, 7pm, 2 hours'), "
                "or type 'human' to talk to our staff directly."
            )

        info = tool_executor.execute("get_business_information", {})
        business_name = info.get("business_name", "our gaming zone")
        return (
            f"Assalam o Alaikum! 👋 Welcome to {business_name}.\n\n"
            "Our smart assistant is running in basic mode right now. You can ask about:\n"
            "- price\n- location\n- timing\n- booking\n- cancel\n\nOr type 'human' to talk to our staff."
        )
