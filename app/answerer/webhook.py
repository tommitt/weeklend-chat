import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.requests import Request
from sqlalchemy.orm import Session

from app.answerer.chats import Chat, ChatType
from app.answerer.schemas import MessageInput, WebhookPayload
from app.constants import WHATSAPP_HOOK_TOKEN
from app.db.db import get_db
from app.db.schemas import ConversationTemp, ConversationUpd
from app.db.services import (
    delete_temp_conversation,
    get_conversation_by_waid,
    register_temp_conversation,
    update_temp_conversation,
)
from app.utils.whatsapp_client import WhatsappWrapper

webhook = APIRouter(prefix="/{chat_type}")


@webhook.get("/")
def chat_endpoint_test(chat_type: ChatType):
    return {"message": f"Hello world! Weeklend is here at {chat_type} chat endpoint."}


@webhook.post("/send_template_message")
async def send_template_message(chat_type: ChatType, to_phone_number: str):
    wa_client = WhatsappWrapper(number_id=Chat(chat_type).whatsapp_number_id)
    response = wa_client.send_template_message(to_phone_number, "hello_world", "en_US")
    return {"status_code": response.status_code, "content": response.text}


@webhook.post("/send_text_message")
async def send_text_message(chat_type: ChatType, to_phone_number: str, message: str):
    wa_client = WhatsappWrapper(number_id=Chat(chat_type).whatsapp_number_id)
    response = wa_client.send_message(to_phone_number, message)
    return {"status_code": response.status_code, "content": response.text}


@webhook.get("/webhook")
async def webhook_get_request(chat_type: ChatType, request: Request):
    hub_mode = request.query_params.get("hub.mode")
    hub_challenge = request.query_params.get("hub.challenge")
    hub_verify_token = request.query_params.get("hub.verify_token")

    if not hub_mode or not hub_challenge or not hub_verify_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing query parameters.",
        )

    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_HOOK_TOKEN:
        return int(hub_challenge)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed. Invalid Token.",
    )


@webhook.post("/webhook")
async def webhook_post_request(
    chat_type: ChatType,
    payload: WebhookPayload,
    db: Session = Depends(get_db),
):
    chat = Chat(chat_type, db=db)
    try:
        payload_value = payload.entry[0]["changes"][0]["value"]
        if "messages" not in payload_value:
            return Response(
                content="Not answering - request is not a message.",
                status_code=status.HTTP_200_OK,
            )

        input_message = payload_value["messages"][0]
        if "type" not in input_message or input_message["type"] != "text":
            return Response(
                content="Not answering - message type is not text.",
                status_code=status.HTTP_200_OK,
            )

        message = MessageInput(
            phone_number=input_message["from"],
            wa_id=input_message["id"],
            body=input_message["text"]["body"],
            timestamp=int(input_message["timestamp"]),
        )

        db_conversation = get_conversation_by_waid(
            db=db, wa_id=message.wa_id, orm=chat.conversation_orm
        )
        if db_conversation is not None:
            return Response(
                content="Not answering - message already processed.",
                status_code=status.HTTP_200_OK,
            )
        db_conversation = register_temp_conversation(
            db=db,
            conversation_temp_in=ConversationTemp(
                from_message=message.body,
                wa_id=message.wa_id,
                received_at=datetime.datetime.utcfromtimestamp(message.timestamp),
            ),
            user_orm=chat.user_orm,
            conversation_orm=chat.conversation_orm,
        )

        if chat.user_journey is None:
            raise Exception(
                f"User journey for {chat_type} chat is not defined: {chat}."
            )
        output = chat.user_journey.run(message)

        if output.answer is not None:
            wa_client = WhatsappWrapper(number_id=chat.whatsapp_number_id)
            wa_response = wa_client.send_message(
                to_phone_number=message.phone_number,
                message=output.answer,
            )
            if wa_response.status_code != status.HTTP_200_OK:
                raise HTTPException(
                    status_code=wa_response.status_code,
                    detail="Answer failed to be sent.",
                )

        db_conversation = update_temp_conversation(
            db=db,
            db_conversation=db_conversation,
            conversation_update_in=ConversationUpd(
                user_id=output.user_id,
                to_message=output.answer,
                answer_type=output.type,
                used_event_ids=json.dumps(output.used_event_ids),
            ),
        )

        return Response(
            content=f"OK - correctly answered with type: {output.type}.",
            status_code=status.HTTP_200_OK,
        )

    except Exception as e:
        if db_conversation:
            delete_temp_conversation(db=db, db_conversation=db_conversation)

        if type(e) == HTTPException:
            raise e

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Something went wrong - {e}",
        )
