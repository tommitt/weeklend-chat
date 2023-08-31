import datetime

from constants import TIMESTAMP_ORIGIN


def date_to_timestamp(date: str | datetime.datetime | datetime.date) -> int:
    if type(date) == str:
        date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    elif type(date) == datetime.datetime:
        date = date.date()
    return (date - datetime.datetime.strptime(TIMESTAMP_ORIGIN, "%Y-%m-%d").date()).days


def timestamp_to_date(timestamp: int) -> datetime.date:
    return datetime.datetime.strptime(
        TIMESTAMP_ORIGIN, "%Y-%m-%d"
    ).date() + datetime.timedelta(days=timestamp)
