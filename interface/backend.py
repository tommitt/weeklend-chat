import datetime
import logging

from fastapi import Depends, FastAPI, status
from sqlalchemy.orm import Session

from app.answerer.chats import ChatType
from app.answerer.pull import AiAgent as PullAiAgent
from app.answerer.push import AiAgent as PushAiAgent
from app.answerer.schemas import AnswerOutput
from app.db.db import get_db
from app.loader.gform import GFormLoader
from app.loader.loader import Loader
from app.loader.scraper import Scraper
from interface.utils.dashboard import get_dashboard_stats
from interface.utils.schemas import ChatbotInput, DashboardOutput

FASTAPI_URL = "http://127.0.0.1:8000"  # default localhost

logging.basicConfig(level=logging.INFO)
app = FastAPI()


@app.post("/chatbot/{chat_type}", response_model=AnswerOutput)
async def chatbot_api(
    chat_type: ChatType,
    chatbot_in: ChatbotInput,
    db: Session = Depends(get_db),
):
    if chat_type == ChatType.push:
        agent = PushAiAgent(
            db=db, user=chatbot_in.user, today_date=chatbot_in.today_date
        )
        response = agent.run(
            user_query=chatbot_in.user_query,
            previous_conversation=chatbot_in.previous_conversation,
        )

    elif chat_type == ChatType.pull:
        agent = PullAiAgent(
            db=None, business=chatbot_in.user, today_date=chatbot_in.today_date
        )
        response = agent.run(
            user_query=chatbot_in.user_query,
            previous_conversation=chatbot_in.previous_conversation,
            pending_event_id=chatbot_in.pending_event_id,
        )
    else:
        raise Exception(f"Chat of type {chat_type} is not accepted.")

    return response


@app.post("/control_panel/scraper/{identifier}")
async def control_panel_api_run_scraper(
    identifier: str,
    db: Session = Depends(get_db),
):
    agent = Scraper(identifier=identifier, db=db)
    agent.run()
    return {
        "status": status.HTTP_200_OK,
        "detail": f"Scraping of {identifier} is done.",
    }


@app.post("/control_panel/gform/{identifier}")
async def control_panel_api_run_scraper(
    identifier: str,
    db: Session = Depends(get_db),
):
    agent = GFormLoader(identifier=identifier, db=db)
    agent.run()
    return {
        "status": status.HTTP_200_OK,
        "detail": f"GForm loading of {identifier} is done.",
    }


@app.post("/control_panel/loader/show")
async def control_panel_api_loader_show_not_vectorized_events(
    db: Session = Depends(get_db),
):
    agent = Loader(db=db)
    events = agent.get_not_vectorized_events()
    return [e.name for e in events]


@app.post("/control_panel/loader/vectorize")
async def control_panel_api_loader_vectorize_events(db: Session = Depends(get_db)):
    agent = Loader(db=db)
    agent.vectorize_events()
    return {"status": status.HTTP_200_OK, "detail": "Everything has been vectorized."}


@app.post("/dashboard", response_model=DashboardOutput)
async def dashboard_api(
    start_date: datetime.date, end_date: datetime.date, db: Session = Depends(get_db)
):
    response = get_dashboard_stats(db=db, start_date=start_date, end_date=end_date)
    return response
