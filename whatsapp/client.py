import requests

from constants import WHATSAPP_API_TOKEN, WHATSAPP_NUMBER_ID


class WhatsappWrapper:
    API_URL = "https://graph.facebook.com/v17.0/"
    API_TOKEN = WHATSAPP_API_TOKEN
    NUMBER_ID = WHATSAPP_NUMBER_ID

    def __init__(self) -> None:
        self.headers = {
            "Authorization": f"Bearer {self.API_TOKEN}",
            "Content-Type": "application/json",
        }
        self.url = self.API_URL + self.NUMBER_ID

    def send_message(
        self,
        to_phone_number: str,
        message: str,
        preview_url: bool = True,
    ) -> requests.Response:
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone_number,
            "type": "text",
            "text": {"body": message, "preview_url": preview_url},
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
