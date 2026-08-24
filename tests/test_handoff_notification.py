from datetime import time
from app.models.models import BusinessSetting, SupportRequest
from app.agents.tools import ToolExecutor
from app.services import whatsapp as wa_service


def _seed_business(db_session, owner_phone=""):
    biz = BusinessSetting(
        opening_time=time(12, 0), closing_time=time(23, 59),
        owner_notification_phone=owner_phone,
    )
    db_session.add(biz)
    db_session.commit()
    return biz


def test_handoff_notifies_owner_when_configured(db_session, monkeypatch):
    _seed_business(db_session, owner_phone="923009998888")

    sent = {}

    def fake_send(to, text):
        sent["to"] = to
        sent["text"] = text
        return True

    monkeypatch.setattr(wa_service, "send_message_sync", fake_send)

    executor = ToolExecutor(db_session, "923001234567")
    result = executor.execute("handoff_to_human", {"reason": "Customer wants to talk to staff"})

    assert result["success"] is True
    assert result["owner_notified"] is True
    assert sent["to"] == "923009998888"
    assert "Customer wants to talk to staff" in sent["text"]

    stored = db_session.query(SupportRequest).first()
    assert stored is not None
    assert stored.customer_phone == "923001234567"


def test_handoff_still_records_request_when_owner_not_configured(db_session):
    _seed_business(db_session, owner_phone="")

    executor = ToolExecutor(db_session, "923001234567")
    result = executor.execute("handoff_to_human", {"reason": "Frustrated customer"})

    assert result["success"] is True
    assert result["owner_notified"] is False

    stored = db_session.query(SupportRequest).first()
    assert stored is not None
    assert stored.message == "Frustrated customer"
