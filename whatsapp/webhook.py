from fastapi import FastAPI, HTTPException, Request
from fastapi.requests import Request
from pydantic import BaseModel

from constants import WHATSAPP_HOOK_TOKEN
from whatsapp.client import WhatsappWrapper

app = FastAPI()


class WebhookPayload(BaseModel):
    entry: list
    object: str


@app.post("/send_template_message")
async def send_template_message(to_phone_number: str):
    whatsapp_client = WhatsappWrapper()
    response = whatsapp_client.send_template_message(
        to_phone_number, "hello_world", "en_US"
    )
    return {"status_code": response.status_code, "content": response.text}


@app.post("/send_text_message")
async def send_text_message(to_phone_number: str, message: str):
    whatsapp_client = WhatsappWrapper()
    response = whatsapp_client.send_message(to_phone_number, message)
    return {"status_code": response.status_code, "content": response.text}


@app.get("/webhooks")
async def handle_get_request(request: Request):
    hub_mode = request.query_params.get("hub.mode")
    hub_challenge = request.query_params.get("hub.challenge")
    hub_verify_token = request.query_params.get("hub.verify_token")

    if not hub_mode or not hub_challenge or not hub_verify_token:
        raise HTTPException(status_code=400, detail="Missing query parameters.")

    if hub_verify_token == WHATSAPP_HOOK_TOKEN:
        return hub_challenge

    raise HTTPException(status_code=401, detail="Authentication failed. Invalid Token.")


@app.post("/webhooks")
async def handle_post_request(payload: WebhookPayload):
    try:
        whatsapp_client = WhatsappWrapper()

        try:
            message = payload.entry[0]["changes"][0]["value"]["messages"][0]
        except:
            raise HTTPException(
                status_code=400, detail="No message present in request."
            )

        if "type" not in message or message["type"] != "text":
            return {
                "status_code": 200,
                "content": "Not answered: message type is not text",
            }

        # mirror answer
        response = whatsapp_client.send_message(
            to_phone_number=message["from"],
            message="Mirror-bot:" + message["text"]["body"],
        )

        return {"status_code": response.status_code, "content": response.text}

    except:
        raise HTTPException(status_code=500, detail="Something went wrong.")
