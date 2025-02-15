import datetime
import logging

import numpy as np
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build as google_build
from sqlalchemy.orm import Session

from app.db.enums import CityEnum, PriceLevel
from app.db.schemas import Event
from app.db.services import get_event, register_event

GFORM_SUPPORTED_SOURCES = {
    # maps source identifier to sheet name
    "wklndteam": "Risposte del modulo partner program Wklnd Team",
    "website": "Risposte del modulo - Sito",
    "lestrade": "Risposte del modulo partner program LeStrade",
    "camera": "Risposte del modulo Biz Camera",
}


def google_sheet_conn():
    """Connect to Google Sheets API using service account credentials."""
    _CREDENTIALS_PATH = ".secrets/credentials.json"
    _SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    credentials = Credentials.from_service_account_file(
        _CREDENTIALS_PATH, scopes=_SCOPES
    )
    return google_build("sheets", "v4", credentials=credentials)


def uniquify_columns(cols: list[str]) -> list[str]:
    """Uniquify a list of columns by appending ".x" for duplicated names."""
    _COL_FORMAT = "{col}.{count}"
    unique_cols, new_cols = set(), []
    for col in cols:
        if col not in unique_cols:
            new_cols.append(col)
            unique_cols.add(col)
        else:
            count = 1
            new_col = _COL_FORMAT.format(col=col, count=count)
            while new_col in unique_cols:
                count += 1
                new_col = _COL_FORMAT.format(col=col, count=count)
            new_cols.append(new_col)
            unique_cols.add(new_col)
    return new_cols


class GFormLoader:
    _DUMMY_START_DATE = datetime.date(2023, 1, 1)
    _DUMMY_END_DATE = datetime.date(2033, 1, 1)
    _DESCRIPTION_MIN_CHARS = 240

    _GOOGLE_SHEET_ID = "1wcUwkehwuY1J-wZJntTsaD6KebYDDYnMFEKgO15oPpw"

    def __init__(self, identifier: str, db: Session) -> None:
        self.identifier = identifier
        self.source = "gform_" + identifier
        self._set_df()
        self.db = db

    def _set_df(self) -> None:
        if self.identifier not in GFORM_SUPPORTED_SOURCES:
            raise Exception(
                f"Gform loader with identifier {self.identifier} is not supported."
            )

        try:
            service = google_sheet_conn()
            values = (
                service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=self._GOOGLE_SHEET_ID,
                    range=GFORM_SUPPORTED_SOURCES[self.identifier],
                )
                .execute()
                .get("values", [])
            )
        except Exception as e:
            raise Exception(f"Google connection failed: {e}")

        if len(values) > 1:
            df = pd.DataFrame(values[1:]).replace("", np.nan)
            df.loc[:, [col for col in range(df.columns.max() + 1, len(values[0]))]] = (
                np.nan
            )
            df.columns = uniquify_columns(values[0])

            self.df = df
        else:
            self.df = pd.DataFrame()

    _COL_EXPERIENCE_TYPE = "Stai registrando un locale o un evento?"
    _COLS_MAP = {
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
            "price_level": "Qual è il prezzo medio per persona a questo evento?",
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
            "price_level": "Qual è il prezzo medio per persona in questo locale?",
            "url": "Inserisci l'indirizzo web legato al locale che gli utenti riceveranno",
        },
    }

    _TURIN_ZONE_MAP = {
        "Centro Storico": "Centro Storico, Porta nuova, Valentino, Parco del Valentino, Quadrilatero, Centro, Piazza Vittorio, Piazza Vitto, Gran Madre, Re Umberto, Vinzaglio, Corso Vittorio.",
        "Aurora": "Aurora, Giulio, Giulio Cesare, Brescia, Corso Brescia.",
        "San Salvario": "San Salvario, Valentino, Parco del Valentino, Marconi, Porta Nuova, Dante, Nizza- Carducci, Molinette, Sansa.",
        "Crocetta": "Crocetta, Re Umberto, Vinzaglio, Politecnico, Poli, Fante, GIardini del Fante, Mercato Crocetta, Einaudi.",
        "Borgo Po": "Borgo Po",
        "Vanchiglia": "Vanchiglia, Santa, Santa Giulia, Piazza Santa Giulia, Panche, Azimut, Offtopic, Campus, Campus Einaudi.",
        "Santa Rita": "Santa Rita, ZSR, Piazza D'armi, Filadelfia, Fila, Palalpitour, Palaisozaki, Stadio del toro, Stadio comunale, Corso Unione, Poveri vecchi, Economia, Università di Economia.",
        "Mirafiori": "Mirafiori, Via Negarville, Strada cacce, Guido Reni, Sarpi.",
        "Lingotto": "Lingotto, 8 Gallery, Otto gallery, Eataly, Oval, Green Pea.",
        "Parella": "Parella, Massaua, Pozzo strada, Montegrappa, Rivoli.",
        "Borgo San Paolo": "Borgo San Paolo, Robilant, Lancia, DLF, Adriatico, Sabotino, Monginevro, Campetti, Alla spa, Braccini.",
        "San Donato": "San Donato, Maria Vittoria, Statuto, Bernini, Piazza dei Mestieri.",
        "Cenisia": "Cenisia, Ceni, Bernini, Rosselli, Racconigi.",
        "Pozzo Strada": "Pozzo Strada.",
        "Barriera di Milano": "Barriera di Milano, Maria Ausiliatrice, Sermig, Porta Palazzo, Bologna, Giulo Cesare, Corso Giulio, Mercato centrale, Nuvola lavazza.",
        "Santa Giulia": "Santa Giulia, Santa, Piazza Santa Giulia.",
        "Vallette": "Vallette, Carcere, 29.",
        "Madonna di Campagna": "Madonna di Campagna, Supermarket, Cardinal Massaia.",
        "Cit Turin": "Cit Turin, Benefica, Principi, Principi d'Acaja, tribunale, Gratta, Grattacielo Intesa.",
        "Borgo Vittoria": "Borgo Vittoria, Borgo Vitto, Cardinal Massaia, Via Stradella, Corvo rosso, Le Roi, Piper, Iper, Ipercoop.",
        "Campidoglio": "Campidoglio, Racco, Racconigi.",
        "Rebaudengo": "Rebaudengo, Piazza Reba, Cigna, Edit, Facit.",
        "Falchera": "Falchera.",
        "Regio Parco": "Regio Parco, Panche, Espace, Carmen, Cagliari, Catania, Dual.",
        "Barriera di Nizza": "Barriera di Nizza, Dante, Nizza, Carducci, Lingotto, Spezia.",
        "Nizza Millefonti": "Nizza Millefonti, Dante, Nizza, Carducci, Lingotto, Spezia.",
        "Mirafiori Nord": "Mirafiori Nord, Fiat, Miraflowers.",
        "Mirafiori Sud": "Mirafiori Sud, Fiat, Miraflowers.",
        "Borgo Filadelfia": "Borgo Filadelfia, Fila, Toro, Stadio del Toro, Tunisi.",
        "Valdocco": "Valdocco, Maria Ausiliatrice, Salerno, Archivio, Quadrilatero, Obelisco, Emanuele Filiberto.",
        "Città Studi": "Città Studi.",
        "Madonna del Pilone": "Madonna del Pilone.",
        "Cavoretto": "Cavoretto, Parco Europa, Maddalena, Rimembranza.",
        "Borgata Lesna": "Borgata Lesna.",
        "Colletta": "Colletta, Cimitero.",
        "San Martino": "San Martino.",
        "Altro (fuori città)": "fuori Torino, fuori porta, fuori città.",
    }

    _CLOSED_DAYS_MAP = {
        "Lunedì": "is_closed_mon",
        "Martedì": "is_closed_tue",
        "Mercoledì": "is_closed_wed",
        "Giovedì": "is_closed_thu",
        "Venerdì": "is_closed_fri",
        "Sabato": "is_closed_sat",
        "Domenica": "is_closed_sun",
    }

    _PRICE_LEVEL_MAP = {
        "0€": PriceLevel.free,
        "1€ - 20€": PriceLevel.inexpensive,
        "20€ - 50€": PriceLevel.moderate,
        "50€ - 100€": PriceLevel.expensive,
        "> 100€": PriceLevel.very_expensive,
    }

    def run(self) -> None:
        logging.info(f"Starting gform insertion for {self.identifier}.")

        if self.df.empty:
            logging.info("No data is present.")
            return

        counter = 0
        for exp_type in ["Locale", "Evento"]:
            cols = self._COLS_MAP[exp_type]
            df = self.df.loc[self.df[self._COL_EXPERIENCE_TYPE] == exp_type][
                [col for col in cols.values() if col is not None]
            ].dropna(axis=0, how="any")

            for _, row in df.iterrows():
                name = row[cols["name"]]
                if len(row[cols["description"]]) < self._DESCRIPTION_MIN_CHARS:
                    raise ValueError("Length of description is too short.")
                description = "\n".join(
                    [
                        name,
                        row[cols["description"]],
                        f"Zona: {self._TURIN_ZONE_MAP[row[cols['zone']]]}",
                    ]
                )

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
                    start_date = self._DUMMY_START_DATE
                    end_date = self._DUMMY_END_DATE

                location = (
                    (row[cols["place"]] + " - " if cols["place"] else "")
                    + row[cols["address"]]
                    + " - "
                    + row[cols["province"]]
                ).strip()
                city = CityEnum.Torino

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
                                closed_days[self._CLOSED_DAYS_MAP[d.strip(" ")]] = True

                url = str(row[cols["url"]]).strip()
                if url in ["-", "", "nan", "null"]:
                    raise ValueError("Url is empty.")

                price_level = self._PRICE_LEVEL_MAP[row[cols["price_level"]]]

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
                    name=name,
                    location=location,
                    url=url,
                    price_level=price_level,
                )

                db_event = get_event(
                    db=self.db,
                    source=self.source,
                    url=url,
                    start_date=start_date,
                    end_date=end_date,
                )
                if db_event is None:
                    db_event = register_event(
                        db=self.db, event_in=new_event, source=self.source
                    )
                    counter += 1

        logging.info(f"Inserted {counter} new events.")
