import logging
from sqlalchemy.orm import Session
from app.models.models import Conversation, Message, MessageSender
from app.services import booking_service as bs
from app.agents.tools import ToolExecutor
from app.agents.prompts import build_system_prompt
from app.agents.fallback_agent import FallbackAgent
from app.config import settings

logger = logging.getLogger("conversation")

MAX_HISTORY_MESSAGES = 10  # keep token usage low: only recent turns sent to the AI


def get_or_create_conversation(db: Session, customer_id: int) -> Conversation:
    convo = db.query(Conversation).filter(
        Conversation.customer_id == customer_id, Conversation.status == "active"
    ).order_by(Conversation.id.desc()).first()
    if not convo:
        convo = Conversation(customer_id=customer_id, channel="whatsapp")
        db.add(convo)
        db.commit()
        db.refresh(convo)
    return convo


def store_message(db: Session, conversation_id: int, sender: MessageSender, text: str, wa_message_id: str = None):
    msg = Message(conversation_id=conversation_id, sender=sender, message=text, wa_message_id=wa_message_id)
    db.add(msg)
    db.commit()
    return msg


def is_duplicate_message(db: Session, wa_message_id: str) -> bool:
    if not wa_message_id:
        return False
    return db.query(Message).filter(Message.wa_message_id == wa_message_id).first() is not None


def _build_history(db: Session, conversation: Conversation, business_info: dict) -> list:
    system_prompt = build_system_prompt(business_info)
    messages = [{"role": "system", "content": system_prompt}]

    recent = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.id.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    recent.reverse()
    for m in recent:
        role = "user" if m.sender == MessageSender.customer else "assistant"
        messages.append({"role": role, "content": m.message})
    return messages


def _get_agent():
    if settings.ai_provider == "groq" and settings.groq_api_key:
        try:
            from app.agents.groq_agent import GroqAgent
            return GroqAgent()
        except Exception:
            logger.exception("Failed to initialize Groq agent, using fallback")
    return FallbackAgent()


async def handle_incoming_message(db: Session, phone: str, text: str, wa_message_id: str = None) -> str:
    if is_duplicate_message(db, wa_message_id):
        logger.info("Duplicate WhatsApp message ignored: %s", wa_message_id)
        return ""

    customer = bs.get_or_create_customer(db, phone)
    conversation = get_or_create_conversation(db, customer.id)
    store_message(db, conversation.id, MessageSender.customer, text, wa_message_id)

    business = bs.get_or_create_business_settings(db)
    business_info = {"business_name": business.business_name, "address": business.address}

    history = _build_history(db, conversation, business_info)
    tool_executor = ToolExecutor(db, phone)

    agent = _get_agent()
    try:
        reply = await agent.respond(phone, history, tool_executor)
    except Exception:
        logger.exception("AI agent failed, falling back to keyword agent")
        reply = await FallbackAgent().respond(phone, history, tool_executor)

    store_message(db, conversation.id, MessageSender.ai, reply)
    return reply
