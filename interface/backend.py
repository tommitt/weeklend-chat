import datetime

from fastapi import Depends, FastAPI, status
from sqlalchemy.orm import Session

from app.answerer.answerer import Answerer
from app.db.db import get_db
from app.db.schemas import AnswerOutput, DashboardOutput
from app.loader.loader import Loader
from app.loader.scraper import Scraper
from app.utils.dashboard import get_dashboard_stats

FASTAPI_URL = "http://127.0.0.1:8000"  # default localhost

app = FastAPI()


@app.post("/chatbot", response_model=AnswerOutput)
async def chatbot_api(user_query: str, db: Session = Depends(get_db)):
    agent = Answerer(db=db)
    response = agent.run(user_query)
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


@app.post("/control_panel/loader/show")
async def control_panel_api_loader_show_not_vectorized_events(
    db: Session = Depends(get_db),
):
    agent = Loader(db=db)
    agent.get_not_vectorized_events()
    return [e.name for e in agent.events]


@app.post("/control_panel/loader/vectorize")
async def control_panel_api_loader_vectorize_events(db: Session = Depends(get_db)):
    agent = Loader(db=db)
    agent.get_not_vectorized_events()

    if len(agent.events) == 0:
        return {"status": status.HTTP_200_OK, "detail": "Nothing to vectorize."}

    agent.vectorize_events()
    return {"status": status.HTTP_200_OK, "detail": "Everything has been vectorized."}


@app.post("/dashboard", response_model=DashboardOutput)
async def dashboard_api(
    start_date: datetime.date, end_date: datetime.date, db: Session = Depends(get_db)
):
    response = get_dashboard_stats(db=db, start_date=start_date, end_date=end_date)
    return response
