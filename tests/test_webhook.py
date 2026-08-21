from app.services.whatsapp import extract_incoming_message


def test_extract_text_message():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "923001234567",
                        "id": "wamid.ABC123",
                        "type": "text",
                        "text": {"body": "Hi"}
                    }]
                }
            }]
        }]
    }
    result = extract_incoming_message(payload)
    assert len(result) == 1
    assert result[0]["from"] == "923001234567"
    assert result[0]["text"] == "Hi"
    assert result[0]["wa_message_id"] == "wamid.ABC123"


def test_extract_ignores_unsupported_type():
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "923001234567",
                        "id": "wamid.XYZ",
                        "type": "image",
                        "image": {"id": "media123"}
                    }]
                }
            }]
        }]
    }
    result = extract_incoming_message(payload)
    assert result[0]["text"] is None


def test_extract_empty_payload():
    assert extract_incoming_message({}) == []
