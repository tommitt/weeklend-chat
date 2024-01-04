from fastapi import FastAPI
from mangum import Mangum

from app.answerer.webhook import webhook
from app.utils.custom_url import router

app = FastAPI()
app.include_router(webhook)
app.include_router(router)


@app.get("/")
def main_endpoint_test():
    return {"message": "Hello world! Weeklend is here at main endpoint."}


# for handling AWS lambda requests
handler = Mangum(app, lifespan="off")
