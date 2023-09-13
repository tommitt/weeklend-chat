import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.requests import Request
from sqlalchemy.orm import Session

from app.answerer.answerer import Answerer
from app.answerer.messages import (
    MESSAGE_REACHED_MAX_USERS,
    MESSAGE_WEEK_ANSWERS_LIMIT,
    MESSAGE_WEEK_BLOCKS_LIMIT,
    MESSAGE_WELCOME,
)
from app.answerer.whatsapp_client import WhatsappWrapper
from app.constants import (
    LIMIT_ANSWERS_PER_WEEK,
    LIMIT_BLOCKS_PER_WEEK,
    LIMIT_MAX_USERS,
    WHATSAPP_HOOK_TOKEN,
)
from app.db.db import get_db
from app.db.enums import AnswerType
from app.db.schemas import AnswerOutput, Conversation, User, WebhookPayload
from app.db.services import (
    get_user,
    get_user_answers_count,
    get_user_count,
    register_conversation,
    register_user,
)

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

    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_HOOK_TOKEN:
        return int(hub_challenge)

    raise HTTPException(status_code=401, detail="Authentication failed. Invalid Token.")


def check_user_limit(db: Session, user_id: int) -> AnswerOutput | None:
    datetime_limit = datetime.datetime.utcnow() - datetime.timedelta(days=7)

    count_answers = get_user_answers_count(
        db=db,
        user_id=user_id,
        answer_type=AnswerType.ai,
        datetime_limit=datetime_limit,
    )
    if count_answers >= LIMIT_ANSWERS_PER_WEEK:
        return AnswerOutput(answer=MESSAGE_WEEK_ANSWERS_LIMIT, type=AnswerType.template)

    count_blocks = get_user_answers_count(
        db=db,
        user_id=user_id,
        answer_type=AnswerType.blocked,
        datetime_limit=datetime_limit,
    )
    if count_blocks >= LIMIT_BLOCKS_PER_WEEK:
        return AnswerOutput(answer=MESSAGE_WEEK_BLOCKS_LIMIT, type=AnswerType.template)

    return None


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
        if db_user is None:
            num_users = get_user_count(db=db)
            if num_users > LIMIT_MAX_USERS:
                new_user_answer = MESSAGE_REACHED_MAX_USERS
                is_blocked = True
            else:
                new_user_answer = MESSAGE_WELCOME
                is_blocked = False

            db_user = register_user(
                user_in=User(phone_number=phone_number, is_blocked=is_blocked), db=db
            )
            output = AnswerOutput(answer=new_user_answer, type=AnswerType.template)

        else:
            if db_user.is_blocked:
                output = AnswerOutput(answer=None, type=AnswerType.unanswered)
            else:
                output = check_user_limit(db=db, user_id=db_user.id)

                if output is None:
                    # llm: get answer
                    agent = Answerer()
                    output = agent.run(message_body)

        # whatsapp: send answer
        if output.answer is not None:
            response = whatsapp_client.send_message(
                to_phone_number=phone_number,
                message=output.answer,
            )

        # db: register conversation
        db_conversation = register_conversation(
            conversation_in=Conversation(
                user_id=db_user.id,
                from_message=message_body,
                to_message=output.answer,
                answer_type=output.type,
                used_event_ids=json.dumps(output.used_event_ids),
                received_at=datetime.datetime.fromtimestamp(timestamp),
            ),
            db=db,
        )

        return {"status_code": response.status_code, "content": response.text}

    except:
        raise HTTPException(status_code=500, detail="Something went wrong.")
