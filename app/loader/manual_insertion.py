import datetime
import logging

import pandas as pd
from sqlalchemy.orm import Session

from app.db.enums import CityEnum, PriceLevel
from app.db.schemas import Event
from app.db.services import get_event, register_event

GFORM_SUPPORTED_SOURCES = {
    "wklndteam": "data/weeklend_snap_gform_wklndteam.csv",
    "lestrade": "data/weeklend_snap_gform_lestrade.csv",
}


class GFormLoader:
    def __init__(self, identifier: str, db: Session) -> None:
        self.identifier = identifier
        self.source = "gform_" + identifier
        self.set_df()
        self.db = db

    def set_df(self) -> None:
        if self.identifier not in GFORM_SUPPORTED_SOURCES:
            raise Exception(
                f"Gform loader with identifier {self.identifier} is not supported."
            )

        self.df = pd.read_csv(GFORM_SUPPORTED_SOURCES[self.identifier])

    _DUMMY_START_DATE = datetime.date(2023, 1, 1)
    _DUMMY_END_DATE = datetime.date(2033, 1, 1)
    _DESCRIPTION_MIN_CHARS = 240

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
            "price_level": "Qual è il prezzo medio per persona in questo locale?",
            "is_for_disabled": "Ha Ingresso per disabili?",
            "is_for_children": "Esperienza adatta a famiglie e bambini?",
            "is_for_animals": "Ingresso consentito agli animali?",
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

    def _yes_no_flag(self, string: str) -> bool:
        if string.lower() == "si":
            return True
        if string.lower() == "no":
            return False
        raise ValueError(f"Yes/No flag has a different value: {string}.")

    def _optional_column(self, string: str) -> str | None:
        if pd.isna(string) or string == "-" or string == "":
            return None
        return string.strip()

    def run(self) -> int:
        logging.info(f"Starting gform insertion for {self.identifier}.")

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
                                closed_days[self._CLOSED_DAYS_MAP[d.strip(" ")]] = True

                url = self._optional_column(row[cols["url"]])

                price_level = self._PRICE_LEVEL_MAP[row[cols["price_level"]]]

                is_for_disabled = self._yes_no_flag(row[cols["is_for_disabled"]])
                is_for_children = self._yes_no_flag(row[cols["is_for_children"]])
                is_for_animals = self._yes_no_flag(row[cols["is_for_animals"]])

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
                    price_level=price_level,
                )

                db_event = get_event(db=self.db, source=self.source, url=url)
                if db_event is not None:
                    db_event = register_event(
                        db=self.db, event_in=new_event, source=self.source
                    )
                    counter += 1

        logging.info(f"Inserted {counter} new events.")
