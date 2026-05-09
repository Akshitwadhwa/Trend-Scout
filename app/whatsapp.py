from __future__ import annotations

from collections.abc import Mapping

from twilio.request_validator import RequestValidator
from twilio.rest import Client

from app.config import Settings


class WhatsAppClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = None
        if settings.twilio_account_sid and settings.twilio_auth_token:
            self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    def send_message(self, body: str) -> str | None:
        if self.client is None or not self.settings.whatsapp_to:
            return None

        message = self.client.messages.create(
            from_=self.settings.twilio_whatsapp_from,
            to=self.settings.whatsapp_to,
            body=body,
        )
        return message.sid

    def validate_request(self, url: str, params: Mapping[str, str], signature: str) -> bool:
        if not self.settings.verify_twilio_signature:
            return True
        if not self.settings.twilio_auth_token or not signature:
            return False

        validator = RequestValidator(self.settings.twilio_auth_token)
        return validator.validate(url, dict(params), signature)
