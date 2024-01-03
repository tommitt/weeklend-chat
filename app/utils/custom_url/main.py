import base64
import json

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.db.models import UserORM
from app.db.services import get_event_by_id, get_user_by_id
from app.utils.custom_url.schemas import EncodingPayload

CUSTOM_ROOT_URL = "wklnd.it"


def encode_url_key(payload: EncodingPayload) -> str:
    payload_list = [value for _, value in vars(payload).items()]
    payload_bytes = json.dumps(payload_list).encode("utf-8")
    encoded_bytes = base64.urlsafe_b64encode(payload_bytes)
    return encoded_bytes.decode()


def decode_url_key(encoded_url_key: str) -> EncodingPayload:
    decoded_bytes = base64.urlsafe_b64decode(encoded_url_key)
    decoded_list = json.loads(decoded_bytes.decode("utf-8"))
    return EncodingPayload.parse_obj(
        dict(zip(EncodingPayload.__annotations__, decoded_list))
    )


app = FastAPI()


@app.get("/events/{url_key}")
def forward_to_target_url(url_key: str, db: Session = Depends(get_db)) -> None:
    try:
        payload = decode_url_key(url_key)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect url key."
        )

    db_event = get_event_by_id(db=db, id=payload.event_id)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event does not exist.",
        )
    if db_event.url is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Url not available for this event.",
        )

    db_user = get_user_by_id(db=db, id=payload.user_id, orm=UserORM)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user does not exist.",
        )

    # TODO: store click to database

    return RedirectResponse(db_event.url)


@app.post("/custom_url")
def get_custom_url(payload: EncodingPayload) -> str:
    url_key = encode_url_key(payload)
    return CUSTOM_ROOT_URL + app.url_path_for("forward_to_target_url", url_key=url_key)
