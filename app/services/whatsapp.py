import logging
import httpx
from app.config import settings

logger = logging.getLogger("whatsapp")

GRAPH_URL = "https://graph.facebook.com/v20.0"


def _headers():
    return {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }


def send_message_sync(to: str, text: str) -> bool:
    """Synchronous variant of send_message, for use inside sync tool-call code paths
    (e.g. paging the owner immediately on human handoff). Best-effort: logs and
    swallows failures so a notification issue never breaks the customer's conversation."""
    if not settings.whatsapp_token or not settings.whatsapp_phone_number_id:
        logger.warning("WhatsApp credentials not configured; owner notification not sent.")
        return False

    url = f"{GRAPH_URL}/{settings.whatsapp_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text, "preview_url": False},
    }
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, headers=_headers(), json=payload)
            if resp.status_code >= 400:
                logger.error("Owner notification send failed: %s %s", resp.status_code, resp.text)
                return False
            return True
    except httpx.HTTPError as exc:
        logger.error("Owner notification send exception: %s", exc)
        return False


async def send_message(to: str, text: str) -> bool:
    """Send a plain text WhatsApp message. Returns True on success."""
    if not settings.whatsapp_token or not settings.whatsapp_phone_number_id:
        logger.warning("WhatsApp credentials not configured; message not sent. to=%s text=%s", to, text[:80])
        return False

    url = f"{GRAPH_URL}/{settings.whatsapp_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text, "preview_url": False},
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=_headers(), json=payload)
            if resp.status_code >= 400:
                logger.error("WhatsApp send failed: %s %s", resp.status_code, resp.text)
                return False
            return True
    except httpx.HTTPError as exc:
        logger.error("WhatsApp send exception: %s", exc)
        return False


async def send_template_message(to: str, template_name: str, language_code: str = "en", components: list = None) -> bool:
    if not settings.whatsapp_token or not settings.whatsapp_phone_number_id:
        logger.warning("WhatsApp credentials not configured; template not sent.")
        return False

    url = f"{GRAPH_URL}/{settings.whatsapp_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
        },
    }
    if components:
        payload["template"]["components"] = components

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=_headers(), json=payload)
            return resp.status_code < 400
    except httpx.HTTPError as exc:
        logger.error("WhatsApp template send exception: %s", exc)
        return False


def extract_incoming_message(payload: dict):
    """Parse Meta webhook payload. Returns list of dicts: {from, text, wa_message_id, type} or []."""
    results = []
    try:
        entries = payload.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    msg_type = msg.get("type")
                    wa_id = msg.get("id")
                    from_number = msg.get("from")
                    text = None
                    if msg_type == "text":
                        text = msg.get("text", {}).get("body")
                    elif msg_type == "button":
                        text = msg.get("button", {}).get("text")
                    elif msg_type == "interactive":
                        interactive = msg.get("interactive", {})
                        if interactive.get("type") == "button_reply":
                            text = interactive["button_reply"].get("title")
                        elif interactive.get("type") == "list_reply":
                            text = interactive["list_reply"].get("title")
                    results.append({
                        "from": from_number,
                        "text": text,
                        "wa_message_id": wa_id,
                        "type": msg_type,
                    })
    except Exception:
        logger.exception("Failed to parse WhatsApp webhook payload")
    return results
