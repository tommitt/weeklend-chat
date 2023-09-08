import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.requests import Request
from sqlalchemy.orm import Session

from app.answerer.messages import MESSAGE_WELCOME
from app.answerer.whatsapp_client import WhatsappWrapper
from app.constants import WHATSAPP_HOOK_TOKEN
from app.db.auth import get_user, register_conversation, register_user
from app.db.db import get_db
from app.db.schemas import Conversation, User, WebhookPayload

webhook = APIRouter()


@webhook.post("/send_template_message")
async def send_template_message(to_phone_number: str):
    whatsapp_client = WhatsappWrapper()
    response = whatsapp_client.send_template_message(
        to_phone_number, "hello_world", "en_US"
    )
    return {"status_code": response.status_code, "content": response.text}


@webhook.post("/send_text_message")
async def send_text_message(to_phone_number: str, message: str):
    whatsapp_client = WhatsappWrapper()
    response = whatsapp_client.send_message(to_phone_number, message)
    return {"status_code": response.status_code, "content": response.text}


@webhook.get("/webhooks")
async def handle_get_request(request: Request):
    hub_mode = request.query_params.get("hub.mode")
    hub_challenge = request.query_params.get("hub.challenge")
    hub_verify_token = request.query_params.get("hub.verify_token")

    if not hub_mode or not hub_challenge or not hub_verify_token:
        raise HTTPException(status_code=400, detail="Missing query parameters.")

    if hub_verify_token == WHATSAPP_HOOK_TOKEN:
        return hub_challenge

    raise HTTPException(status_code=401, detail="Authentication failed. Invalid Token.")


@webhook.post("/webhooks")
async def handle_post_request(
    payload: WebhookPayload,
    db: Session = Depends(get_db),
):
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

        phone_number = message["from"]
        timestamp = message["timestamp"]
        message_body = message["text"]["body"]

        # db: register user
        db_user = get_user(db, phone_number=phone_number)
        if not db_user:
            db_user = register_user(user_in=User(phone_number=phone_number), db=db)
            answer = MESSAGE_WELCOME
            is_blocked = False
            used_event_ids = None

        else:
            # llm: get answer
            # TODO: use llm properly
            answer = f"From {phone_number}: {message_body}"
            is_blocked = False
            used_event_ids = [1, 2, 3]

        # whatsapp: send answer
        response = whatsapp_client.send_message(
            to_phone_number=phone_number,
            message=answer,
        )

        # db: register conversation
        db_conversation = register_conversation(
            conversation_in=Conversation(
                user_id=db_user.id,
                from_message=message_body,
                to_message=answer,
                is_blocked=is_blocked,
                used_event_ids=json.dumps(used_event_ids),
                received_at=datetime.datetime.fromtimestamp(timestamp),
            ),
            db=db,
        )

        return {"status_code": response.status_code, "content": response.text}

    except:
        raise HTTPException(status_code=500, detail="Something went wrong.")
