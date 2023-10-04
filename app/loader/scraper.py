import datetime

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt

from app.db.enums import CityEnum
from app.db.schemas import Event
from app.db.services import get_event, register_event


class BaseScraper:
    def get_timing_flags(
        self, opening_time: str, closing_time: str
    ) -> tuple[bool, bool]:
        """Format is expected to be 'HH:MM'"""
        is_during_day = int(opening_time.split(":")[0]) <= 18
        is_during_night = int(closing_time.split(":")[0]) >= 20
        return is_during_day, is_during_night


class GuidatorinoScraper(BaseScraper):
    _MONTHS_CONVERSION = {
        " Gennaio ": "-01-",
        " Febbraio ": "-02-",
        " Marzo ": "-03-",
        " Aprile ": "-04-",
        " Maggio ": "-05-",
        " Giugno ": "-06-",
        " Luglio ": "-07-",
        " Agosto ": "-08-",
        " Settembre ": "-09-",
        " Ottobre ": "-10-",
        " Novembre ": "-11-",
        " Dicembre ": "-12-",
    }

    def __init__(self) -> None:
        self.identifier: str = "guidatorino"
        self.root_url: str = "https://www.guidatorino.com/eventi-torino/"
        self.events_list: list[dict] = []
        self.output: list[Event] = []

    def run_root_page(self) -> None:
        response = requests.get(self.root_url)
        soup = BeautifulSoup(response.content, "html.parser")

        events = (
            soup.find("table", {"class": "events-table"}).find("tbody").find_all("tr")
        )

        for event in events:
            event_dict = {}
            content = event.find("div", {"class", "eventlist-2"})
            sub_contents = content.find_all("p")

            event_dict["url"] = content.find("h3").find("a")["href"]
            event_dict["title"] = content.find("h3").find("a").text

            categories = content.find("ul", {"class": "event-categories"})
            event_dict["is_for_children"] = False
            if categories is not None:
                for cat in categories.find_all("li"):
                    if cat.find("a").text == "Bambini":
                        event_dict["is_for_children"] = True

            dates = [
                datetime.datetime.strptime(d.replace(key, val), "%d-%m-%Y").date()
                for d in sub_contents[0]
                .find("span", {"class": "lista-data"})
                .text.split(" - ")
                for key, val in self._MONTHS_CONVERSION.items()
                if key in d
            ]
            event_dict["start_date"] = dates[0]
            event_dict["end_date"] = dates[0] if len(dates) == 1 else dates[1]

            timing = (
                sub_contents[0]
                .find("span", {"class": "lista-orario"})
                .text.strip("Orario:  ")
                .split(" - ")
            )
            (
                event_dict["is_during_day"],
                event_dict["is_during_night"],
            ) = self.get_timing_flags(opening_time=timing[0], closing_time=timing[1])

            city = sub_contents[1].find("span", {"class": "evento-citta"}).text
            address = sub_contents[1].find("span", {"class": "evento-indirizzo"}).text
            place = sub_contents[1].find("span", {"class": "lista-luogo"}).text
            location = (
                city
                if (city == place) and (city == address)
                else " - ".join([place, address, city])
            )
            event_dict["city"] = CityEnum.Torino
            event_dict["location"] = location
            event_dict["is_countryside"] = city != CityEnum.Torino

            self.events_list.append(event_dict)

        print(f"Got {len(self.events_list)} to be scraped.")

    @retry(stop=stop_after_attempt(3))
    def run_event_pages(self) -> None:
        run_events_list = self.events_list.copy()
        print(f"Running {len(run_events_list)} pages")
        for i, event_dict in enumerate(run_events_list):
            print(f"{i+1}/{len(run_events_list)}")

            event_response = requests.get(event_dict["url"])
            event_soup = BeautifulSoup(event_response.content, "html.parser")

            text_containers = event_soup.find("div", {"class": "testo"}).find_all("p")

            texts = [event_dict["title"]]
            for t in text_containers:
                text = t.text
                if text == "\xa0":
                    pass
                elif text.startswith("Potete acquistare") or text.startswith(
                    "\xa0\nQuando"
                ):
                    break
                texts.append(text)

            description = "\n".join(texts)

            # save output
            self.output.append(
                Event(
                    description=description,
                    is_vectorized=False,
                    # metadata
                    city=event_dict["city"],
                    start_date=event_dict["start_date"],
                    end_date=event_dict["end_date"],
                    is_closed_mon=False,
                    is_closed_tue=False,
                    is_closed_wed=False,
                    is_closed_thu=False,
                    is_closed_fri=False,
                    is_closed_sat=False,
                    is_closed_sun=False,
                    is_during_day=event_dict["is_during_day"],
                    is_during_night=event_dict["is_during_night"],
                    is_countryside=event_dict["is_countryside"],
                    is_for_children=event_dict["is_for_children"],
                    is_for_disabled=False,
                    is_for_animals=False,
                    # additional info
                    name=event_dict["title"],
                    location=event_dict["location"],
                    url=event_dict["url"],
                )
            )
            self.events_list.remove(event_dict)

    def run(self) -> None:
        self.run_root_page()
        self.run_event_pages()


class Scraper:
    _supported_sources = {
        "guidatorino": GuidatorinoScraper,
    }

    def __init__(self, identifier: str, db: Session) -> None:
        self.identifier = identifier
        self.source = "webscraper_" + identifier
        self.set_scraper()
        self.db = db

    def set_scraper(self) -> None:
        if self.identifier not in self._supported_sources:
            raise Exception(
                f"Scraper with identifier {self.identifier} is not supported."
            )

        self.scraper = self._supported_sources[self.identifier]()

    def update_db(self) -> int:
        counter = 0
        for event in self.scraper.output:
            db_event = get_event(db=self.db, source=self.source, url=event.url)
            if db_event is None:
                db_event = register_event(
                    db=self.db, event_in=event, source=self.source
                )
                counter += 1

        self.db.commit()
        return counter

    def run(self) -> None:
        print(f"Starting scraper for {self.identifier}.")
        self.scraper.run()
        num_inserted_events = self.update_db()
        print(f"Inserted {num_inserted_events} new events.")
