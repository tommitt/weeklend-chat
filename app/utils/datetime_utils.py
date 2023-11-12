import datetime

from app.constants import TIMESTAMP_ORIGIN


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


def convert_italian_month(date_string: str):
    ITALIAN_MONTHS = {
        "Gennaio": "01",
        "Febbraio": "02",
        "Marzo": "03",
        "Aprile": "04",
        "Maggio": "05",
        "Giugno": "06",
        "Luglio": "07",
        "Agosto": "08",
        "Settembre": "09",
        "Ottobre": "10",
        "Novembre": "11",
        "Dicembre": "12",
    }

    for str_month, int_month in ITALIAN_MONTHS.items():
        if str_month in date_string:
            date_string = date_string.replace(str_month, int_month)

    return date_string
