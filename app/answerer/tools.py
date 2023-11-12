import datetime
from typing import Optional

from langchain.agents import tool
from langchain.chains.query_constructor.ir import Comparison, Operation, StructuredQuery
from pydantic import BaseModel, Field

from app.constants import N_EVENTS_CONTEXT
from app.utils.conn import get_vectorstore, get_vectorstore_translator
from app.utils.datetime_utils import date_to_timestamp


class SearchEventsInput(BaseModel):
    user_query: str = Field(description="The user's query.")
    start_date: Optional[str] = Field(
        description="The start date of the range in format 'YYYY-MM-DD'."
    )
    end_date: Optional[str] = Field(
        description="The end date of the range in format 'YYYY-MM-DD'."
    )
    time: Optional[str] = Field(
        description="This is the time of the day. It can be either 'daytime', 'nighttime' or 'both'"
    )


@tool(args_schema=SearchEventsInput)
def search_events(
    user_query: str,
    start_date: str | None = None,
    end_date: str | None = None,
    time: str | None = None,
) -> str:
    """Search available events that best answer the user's query."""
    vectorstore = get_vectorstore()
    vectorstore_translator = get_vectorstore_translator()
    # TODO: make this a parameter
    today_date_dt = datetime.date.today()

    # filter out events based on start and end dates
    start_date_dt = (
        today_date_dt
        if start_date is None
        else datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    )
    end_date_dt = (
        today_date_dt + datetime.timedelta(days=6)
        if end_date is None
        else datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    )

    filters = [
        Comparison(
            comparator="lte",
            attribute="start_date",
            value=date_to_timestamp(end_date_dt),
        ),
        Comparison(
            comparator="gte",
            attribute="end_date",
            value=date_to_timestamp(start_date_dt),
        ),
    ]

    # filter out events that are closed in the query's days of the week
    # the code finds all days of the week in the given range
    # it then adds a filter where the event must be open in at least one day in the range
    # example: query is from Monday to Tuesday,
    # the filter becomes: OR(NOT closed on Monday, NOT closed on Tuesday)
    days_of_week_in_range = set(
        [
            (start_date_dt + datetime.timedelta(days=i)).strftime("%A")
            for i in range((end_date_dt - start_date_dt).days + 1)
        ]
    )

    map_closed_days = {
        "Monday": "is_closed_mon",
        "Tuesday": "is_closed_tue",
        "Wednesday": "is_closed_wed",
        "Thursday": "is_closed_thu",
        "Friday": "is_closed_fri",
        "Saturday": "is_closed_sat",
        "Sunday": "is_closed_sun",
    }
    filters_closed_days = []
    for day_of_week, attribute in map_closed_days.items():
        if day_of_week in days_of_week_in_range:
            filters_closed_days.append(
                Comparison(comparator="eq", attribute=attribute, value=False)
            )

    filters.append(Operation(operator="or", arguments=filters_closed_days))

    # filter out events based on time of the day
    if time == "daytime":
        filters.append(
            Comparison(comparator="eq", attribute="is_during_day", value=True)
        )
    elif time == "nighttime":
        filters.append(
            Comparison(comparator="eq", attribute="is_during_night", value=True)
        )

    _, filter_kwargs = vectorstore_translator.visit_structured_query(
        structured_query=StructuredQuery(
            query=user_query, filter=Operation(operator="and", arguments=filters)
        )
    )

    relevant_docs = vectorstore.similarity_search(
        user_query, k=N_EVENTS_CONTEXT, **filter_kwargs
    )

    # TODO: add url and location
    return "\n\n".join(
        [f"ID {doc.metadata['id']}:\n```{doc.page_content}```" for doc in relevant_docs]
    )
