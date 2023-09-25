from fastapi import FastAPI
from mangum import Mangum

from app.answerer.webhook import webhook

app = FastAPI()
app.include_router(webhook)


@app.get("/")
def main_endpoint_test():
    return {"message": "Hello world! Weeklend is here at main endpoint."}


# for handling AWS lambda requests
handler = Mangum(app, lifespan="off")
