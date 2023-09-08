import uvicorn
from fastapi import FastAPI

from app.answerer.webhook import webhook
from app.db.db import engine
from app.db.models import Base

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(webhook)

if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8000)
