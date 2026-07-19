import pytest

from web_app.notifications import models


def test_telegram_message_requires_chat_and_plain_text() -> None:
    assert hasattr(models, "TelegramMessage")
    message = models.TelegramMessage(chat_id="-100123", text="Threat detected")

    assert message.chat_id == "-100123"
    assert message.text == "Threat detected"


@pytest.mark.parametrize(
    ("chat_id", "text"),
    [("", "Threat detected"), ("-100123", ""), ("-100123", "x" * 4097)],
)
def test_telegram_message_rejects_invalid_content(chat_id: str, text: str) -> None:
    assert hasattr(models, "TelegramMessage")
    with pytest.raises(ValueError):
        models.TelegramMessage(chat_id=chat_id, text=text)
