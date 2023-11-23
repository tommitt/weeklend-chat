import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.requests import Request
from sqlalchemy.orm import Session

from app.answerer.answerer import Answerer
from app.answerer.messages import (
    MESSAGE_GOT_UNBLOCKED,
    MESSAGE_NOT_DELIVERED,
    MESSAGE_REACHED_MAX_USERS,
    MESSAGE_WEEK_ANSWERS_LIMIT,
    MESSAGE_WEEK_BLOCKS_LIMIT,
    MESSAGE_WELCOME,
)
from app.answerer.schemas import AnswerOutput, WebhookPayload
from app.answerer.whatsapp_client import WhatsappWrapper
from app.constants import (
    CONVERSATION_HOURS_WINDOW,
    CONVERSATION_MAX_MESSAGES,
    LIMIT_ANSWERS_PER_WEEK,
    LIMIT_BLOCKS_PER_WEEK,
    LIMIT_MAX_USERS,
    THRESHOLD_NOT_DELIVERED_ANSWER,
    WHATSAPP_HOOK_TOKEN,
)
from app.db.db import get_db
from app.db.enums import AnswerType
from app.db.models import UserORM
from app.db.schemas import ConversationTemp, ConversationUpd, User
from app.db.services import (
    block_user,
    delete_temp_conversation,
    get_conversation_by_waid,
    get_user,
    get_user_answers_count,
    get_user_conversations,
    get_user_count,
    register_temp_conversation,
    register_user,
    unblock_user,
    update_temp_conversation,
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


def blocked_user_journey(db: Session, db_user: UserORM) -> AnswerOutput:
    if (
        db_user.block_expires_at is not None
        and db_user.block_expires_at < datetime.datetime.utcnow()
    ):
        db_user = unblock_user(db=db, db_user=db_user)
        return AnswerOutput(answer=MESSAGE_GOT_UNBLOCKED, type=AnswerType.template)

    return AnswerOutput(answer=None, type=AnswerType.unanswered)


def new_user_journey(db: Session, phone_number: str) -> tuple[AnswerOutput, UserORM]:
    num_users = get_user_count(db=db)
    if num_users > LIMIT_MAX_USERS:
        new_user_answer = MESSAGE_REACHED_MAX_USERS
        is_blocked = True
    else:
        new_user_answer = MESSAGE_WELCOME
        is_blocked = False

    db_user = register_user(
        db=db, user_in=User(phone_number=phone_number, is_blocked=is_blocked)
    )
    output = AnswerOutput(answer=new_user_answer, type=AnswerType.template)

    return output, db_user


def check_user_limit_by_answertype(
    db: Session,
    db_user: UserORM,
    answer_type: AnswerType,
    timedelta: datetime.timedelta,
    limit: int,
    block_message: str,
) -> AnswerOutput | None:
    count, first_datetime = get_user_answers_count(
        db=db,
        user_id=db_user.id,
        answer_type=answer_type,
        datetime_limit=(datetime.datetime.utcnow() - timedelta),
    )

    if count >= limit:
        block_expires_at = first_datetime + timedelta
        db_user = block_user(db=db, db_user=db_user, block_expires_at=block_expires_at)
        return AnswerOutput(
            answer=block_message.format(
                limit_per_week=limit,
                block_expires_at=block_expires_at.strftime("%d/%m/%Y"),
            ),
            type=AnswerType.template,
        )

    return None


def check_user_limits(db: Session, db_user: UserORM) -> AnswerOutput | None:
    timedelta = datetime.timedelta(days=7)

    output = check_user_limit_by_answertype(
        db=db,
        db_user=db_user,
        answer_type=AnswerType.ai,
        timedelta=timedelta,
        limit=LIMIT_ANSWERS_PER_WEEK,
        block_message=MESSAGE_WEEK_ANSWERS_LIMIT,
    )
    if output is not None:
        return output

    output = check_user_limit_by_answertype(
        db=db,
        db_user=db_user,
        answer_type=AnswerType.blocked,
        timedelta=timedelta,
        limit=LIMIT_BLOCKS_PER_WEEK,
        block_message=MESSAGE_WEEK_BLOCKS_LIMIT,
    )
    if output is not None:
        return output

    return None


def get_previous_conversation(db: Session, user_id: int) -> list[tuple[str, str]]:
    db_conversations = get_user_conversations(
        db=db,
        user_id=user_id,
        from_datetime=(
            datetime.datetime.now()
            - datetime.timedelta(hours=CONVERSATION_HOURS_WINDOW)
        ),
        max_messages=CONVERSATION_MAX_MESSAGES,
    )
    llm_conversations = []
    for db_conversation in db_conversations:
        llm_conversations.append(("human", db_conversation.from_message))
        if db_conversation.answer_type != AnswerType.unanswered:
            llm_conversations.append(("ai", db_conversation.to_message))
    return llm_conversations


def standard_user_journey(
    db: Session, db_user: UserORM, user_query: str
) -> AnswerOutput:
    output = check_user_limits(db=db, db_user=db_user) if not db_user.is_admin else None

    if output is None:
        agent = Answerer(db=db)
        output = agent.run(
            user_query,
            previous_conversation=get_previous_conversation(db=db, user_id=db_user.id),
        )

    return output


@webhook.post("/webhooks")
async def handle_post_request(
    payload: WebhookPayload,
    db: Session = Depends(get_db),
):
    try:
        payload_value = payload.entry[0]["changes"][0]["value"]
        if "messages" not in payload_value:
            return Response(
                content="Not answering - request is not a message.",
                status_code=status.HTTP_200_OK,
            )

        message = payload_value["messages"][0]
        if "type" not in message or message["type"] != "text":
            return Response(
                content="Not answering - message type is not text.",
                status_code=status.HTTP_200_OK,
            )

        # read message
        phone_number = message["from"]
        wa_id = message["id"]
        message_body = message["text"]["body"]
        message_timestamp = int(message["timestamp"])
        current_timestamp = datetime.datetime.utcnow().timestamp()

        db_conversation = get_conversation_by_waid(db=db, wa_id=wa_id)
        if db_conversation is not None:
            return Response(
                content="Not answering - message already processed.",
                status_code=status.HTTP_200_OK,
            )
        db_conversation = register_temp_conversation(
            db=db,
            conversation_temp_in=ConversationTemp(
                from_message=message_body,
                wa_id=wa_id,
                received_at=datetime.datetime.utcfromtimestamp(message_timestamp),
            ),
        )

        # start user journey
        db_user = get_user(db, phone_number=phone_number)
        if db_user is None:
            output, db_user = new_user_journey(db=db, phone_number=phone_number)
        else:
            if db_user.is_blocked:
                output = blocked_user_journey(db=db, db_user=db_user)
            elif (
                round(current_timestamp - message_timestamp)
                > THRESHOLD_NOT_DELIVERED_ANSWER
            ):
                output = AnswerOutput(
                    answer=MESSAGE_NOT_DELIVERED, type=AnswerType.failed
                )
            else:
                output = standard_user_journey(
                    db=db, db_user=db_user, user_query=message_body
                )

        if output.answer is not None:
            wa_client = WhatsappWrapper()
            wa_response = wa_client.send_message(
                to_phone_number=phone_number,
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
                user_id=db_user.id,
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
