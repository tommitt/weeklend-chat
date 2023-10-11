import datetime

import pandas as pd

from app.db.db import SessionLocal
from app.db.enums import CityEnum
from app.db.schemas import Event
from app.db.services import register_event

FILENAME = "data/weeklend_snap_gform.csv"
SOURCE = "business-gform"
DUMMY_START_DATE = datetime.date(2023, 1, 1)
DUMMY_END_DATE = datetime.date(2033, 1, 1)
DESCRIPTION_MIN_CHARS = 240

df_full = pd.read_csv(FILENAME)
db = SessionLocal()
# TODO: integrate into FastAPI and control panel


def yes_no_flag(string: str) -> bool:
    if string.lower() == "si":
        return True
    if string.lower() == "no":
        return False
    raise ValueError(f"Yes/No flag has a different value: {string}.")


def optional_column(string: str) -> str | None:
    if pd.isna(string) or string == "-" or string == "":
        return None
    return string.strip()


col_exp_type = "Stai registrando un locale o un evento?"
cols_map = {
    "Evento": {
        "name": "Nome dell'Evento",
        "description": "Descrizione dell'Evento",
        "zone": "Indica in quale zona si trova l'evento",
        "address": "Indirizzo dell'evento",
        "place": "Nome della location",
        "province": "Indica la provincia in cui si terrà l'evento",
        "start_date": "Data di inizio dell'evento ",
        "end_date": "Data di fine dell'evento ",
        "opening_period": "È un evento principalmente diurno o principalmente notturno?",
        "closing_days": None,
        "price": "Qual è il prezzo medio per persona a questo evento?",
        "is_for_disabled": "Ingresso per disabili?",
        "is_for_children": "Esperienza adatta a famiglie e bambini?.1",
        "is_for_animals": "Ingresso consentito agli animali?.1",
        "url": "Inserisci l'indirizzo web legato all'evento che gli utenti riceveranno",
    },
    "Locale": {
        "name": "Nome del Locale",
        "description": "Descrizione del Locale",
        "zone": "Indica in quale zona si trova il locale",
        "address": "Indirizzo del locale ",
        "place": None,
        "province": "Indica la provincia del tuo locale",
        "start_date": None,
        "end_date": None,
        "opening_period": "Il locale è principalmente diurno o principalmente notturno?",
        "closing_days": "Giorno di chiusura settimanale ",
        "price": "Qual è il prezzo medio per persona in questo locale?",
        "is_for_disabled": "Ha Ingresso per disabili?",
        "is_for_children": "Esperienza adatta a famiglie e bambini?",
        "is_for_animals": "Ingresso consentito agli animali?",
        "url": "Inserisci l'indirizzo web legato al locale che gli utenti riceveranno",
    },
}

map_closed_days = {
    "Lunedì": "is_closed_mon",
    "Martedì": "is_closed_tue",
    "Mercoledì": "is_closed_wed",
    "Giovedì": "is_closed_thu",
    "Venerdì": "is_closed_fri",
    "Sabato": "is_closed_sat",
    "Domenica": "is_closed_sun",
}

counter = 0
for exp_type in ["Locale", "Evento"]:
    cols = cols_map[exp_type]
    df = df_full.loc[df_full[col_exp_type] == exp_type][
        [col for col in cols.values() if col is not None]
    ].dropna(axis=0, how="any")

    for i, row in df.iterrows():
        name = row[cols["name"]]
        if len(row[cols["description"]]) < DESCRIPTION_MIN_CHARS:
            raise ValueError("Length of description is too short.")
        description = name + "\n" + row[cols["description"]]
        # TODO: add zone to description
        # TODO: add price to db

        if cols["start_date"]:
            start_date = datetime.datetime.strptime(
                row[cols["start_date"]], "%d/%m/%Y"
            ).date()

            end_date = (
                start_date
                if pd.isna(row[cols["end_date"]])
                else datetime.datetime.strptime(
                    row[cols["end_date"]], "%d/%m/%Y"
                ).date()
            )
        else:
            start_date = DUMMY_START_DATE
            end_date = DUMMY_END_DATE

        location = (
            (row[cols["place"]] + " - " if cols["place"] else "")
            + row[cols["address"]]
            + " - "
            + row[cols["province"]]
        ).strip()
        city = CityEnum.Torino
        is_countryside = not row[cols["province"]] == "Torino"

        closed_days = {
            "is_closed_mon": False,
            "is_closed_tue": False,
            "is_closed_wed": False,
            "is_closed_thu": False,
            "is_closed_fri": False,
            "is_closed_sat": False,
            "is_closed_sun": False,
        }
        if cols["closing_days"]:
            if not pd.isna(row[cols["closing_days"]]):
                closing_days: list[str] = row[cols["closing_days"]].split(",")
                for d in closing_days:
                    if d != "Nessuna di queste (il locale è sempre aperto)":
                        closed_days[map_closed_days[d.strip(" ")]] = True

        url = optional_column(row[cols["url"]])

        is_for_disabled = yes_no_flag(row[cols["is_for_disabled"]])
        is_for_children = yes_no_flag(row[cols["is_for_children"]])
        is_for_animals = yes_no_flag(row[cols["is_for_animals"]])

        is_during_day = False
        is_during_night = False
        if row[cols["opening_period"]] == "Diurno":
            is_during_day = True
        elif row[cols["opening_period"]] == "Notturno":
            is_during_night = True
        elif row[cols["opening_period"]] == "Entrambi":
            is_during_day = True
            is_during_night = True
        else:
            raise ValueError(
                f"Opening period has a not accepted value: {row[cols['opening_period']]}."
            )

        new_event = Event(
            description=description,
            is_vectorized=False,
            city=city,
            start_date=start_date,
            end_date=end_date,
            is_closed_mon=closed_days["is_closed_mon"],
            is_closed_tue=closed_days["is_closed_tue"],
            is_closed_wed=closed_days["is_closed_wed"],
            is_closed_thu=closed_days["is_closed_thu"],
            is_closed_fri=closed_days["is_closed_fri"],
            is_closed_sat=closed_days["is_closed_sat"],
            is_closed_sun=closed_days["is_closed_sun"],
            is_during_day=is_during_day,
            is_during_night=is_during_night,
            is_countryside=is_countryside,
            is_for_children=is_for_children,
            is_for_disabled=is_for_disabled,
            is_for_animals=is_for_animals,
            name=name,
            location=location,
            url=url,
        )

        db_event = register_event(db=db, event_in=new_event, source=SOURCE)
        counter += 1

print(f"Registered {counter} events")
