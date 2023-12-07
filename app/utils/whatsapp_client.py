import requests

from app.constants import WHATSAPP_API_TOKEN


class WhatsappWrapper:
    API_URL = "https://graph.facebook.com/v17.0/"
    API_TOKEN = WHATSAPP_API_TOKEN

    def __init__(self, number_id: str) -> None:
        self.headers = {
            "Authorization": f"Bearer {self.API_TOKEN}",
            "Content-Type": "application/json",
        }
        self.url = self.API_URL + number_id

    def send_message(
        self,
        to_phone_number: str,
        message: str,
    ) -> requests.Response:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone_number,
            "type": "text",
            "text": {
                "body": message,
                "preview_url": False,
            },
        }

        response = requests.post(
            f"{self.url}/messages", headers=self.headers, json=payload
        )

        return response

    def send_template_message(
        self,
        to_phone_number: str,
        template_name: str,
        language_code: str,
    ) -> requests.Response:
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }

        response = requests.post(
            f"{self.url}/messages", headers=self.headers, json=payload
        )

        return response
