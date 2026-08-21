import logging
from fastapi import APIRouter, Request, Depends, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.services.whatsapp import extract_incoming_message, send_message
from app.services.conversation_service import handle_incoming_message

router = APIRouter()
logger = logging.getLogger("webhook")


@router.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Verification failed", status_code=403)


@router.post("/webhook")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored"}

    messages = extract_incoming_message(payload)
    for m in messages:
        if not m.get("text") or not m.get("from"):
            logger.info("Ignoring unsupported message type: %s", m.get("type"))
            continue
        logger.info("Incoming WhatsApp message from %s", m["from"])
        try:
            reply = await handle_incoming_message(db, m["from"], m["text"], m.get("wa_message_id"))
            if reply:
                await send_message(m["from"], reply)
        except Exception:
            logger.exception("Error handling incoming message")

    return {"status": "received"}
