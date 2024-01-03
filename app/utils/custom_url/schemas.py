from pydantic import BaseModel


class EncodingPayload(BaseModel):
    # only integers are accepted
    event_id: int
    user_id: int
