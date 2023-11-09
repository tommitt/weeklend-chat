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
        "Gennaio": "January",
        "Febbraio": "February",
        "Marzo": "March",
        "Aprile": "April",
        "Maggio": "May",
        "Giugno": "June",
        "Luglio": "July",
        "Agosto": "August",
        "Settembre": "September",
        "Ottobre": "October",
        "Novembre": "November",
        "Dicembre": "December",
    }

    for it_month, en_month in ITALIAN_MONTHS.items():
        if it_month in date_string:
            date_string = date_string.replace(it_month, en_month)

    return date_string
