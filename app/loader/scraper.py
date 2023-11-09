import datetime
import logging

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt

from app.db.enums import CityEnum
from app.db.schemas import Event
from app.db.services import get_event, register_event
from app.utils.datetime_utils import convert_italian_month


class BaseScraper:
    _SOURCE_ROOT = "webscraper_"
    _BASE_IDENTIFIER = "base"

    def __init__(self, db: Session) -> None:
        self.identifier = self._BASE_IDENTIFIER
        self.output: list[Event] = []
        self.db = db

    @property
    def source(self) -> str:
        if self.identifier == self._BASE_IDENTIFIER:
            raise Exception("Property source cannot be called with base class.")
        return self._SOURCE_ROOT + self.identifier

    def get_timing_flags(
        self, opening_time: str, closing_time: str
    ) -> tuple[bool, bool]:
        """Format is expected to be 'HH:MM'"""
        is_during_day = int(opening_time.split(":")[0]) <= 18
        is_during_night = int(closing_time.split(":")[0]) >= 20
        if not is_during_day and not is_during_night:
            raise Exception("Event is neither during day or night.")
        return is_during_day, is_during_night

    def is_event_in_db(self, event_url: str) -> bool:
        db_event = get_event(db=self.db, source=self.source, url=event_url)
        if db_event is None:
            return False
        return True


class GuidatorinoScraper(BaseScraper):
    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.identifier: str = "guidatorino"
        self.root_url: str = "https://www.guidatorino.com/eventi-torino/"
        self.events_list: list[dict] = []

    def run_root_page(self) -> None:
        response = requests.get(self.root_url)
        soup = BeautifulSoup(response.content, "html.parser")

        events = (
            soup.find("table", {"class": "events-table"}).find("tbody").find_all("tr")
        )

        for event in events:
            try:
                event_dict = {}
                content = event.find("div", {"class", "eventlist-2"})
                sub_contents = content.find_all("p")

                event_url = content.find("h3").find("a")["href"]
                if self.is_event_in_db(event_url):
                    continue

                event_dict["url"] = event_url
                event_dict["title"] = content.find("h3").find("a").text

                categories = content.find("ul", {"class": "event-categories"})
                event_dict["is_for_children"] = False
                if categories is not None:
                    for cat in categories.find_all("li"):
                        if cat.find("a").text == "Bambini":
                            event_dict["is_for_children"] = True

                dates = [
                    datetime.datetime.strptime(
                        convert_italian_month(d), "%d %B %Y"
                    ).date()
                    for d in sub_contents[0]
                    .find("span", {"class": "lista-data"})
                    .text.split(" - ")
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
                ) = self.get_timing_flags(
                    opening_time=timing[0], closing_time=timing[1]
                )

                city = sub_contents[1].find("span", {"class": "evento-citta"}).text
                address = (
                    sub_contents[1].find("span", {"class": "evento-indirizzo"}).text
                )
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

            except:
                pass

        logging.info(f"Got {len(self.events_list)} new events to be scraped.")

    @retry(stop=stop_after_attempt(3))
    def run_event_pages(self) -> None:
        run_events_list = self.events_list.copy()
        logging.info(f"Running {len(run_events_list)} pages")
        for i, event_dict in enumerate(run_events_list):
            logging.info(f"{i+1}/{len(run_events_list)}")

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
                    price_level=None,
                )
            )
            self.events_list.remove(event_dict)

    def run(self) -> None:
        self.run_root_page()
        self.run_event_pages()


class LovelangheScraper(BaseScraper):
    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.identifier: str = "lovelanghe"
        self.root_url: str = "https://langhe.net/eventi/"
        self.page_url: str = "https://langhe.net/eventi/page/{page}/"
        self.event_urls: list[str] = []

    def run_root_page(self) -> None:
        response = requests.get(self.root_url)
        soup = BeautifulSoup(response.content, "html.parser")

        last_page = int(
            soup.find("div", {"class": "pagination pagination--event grid__pagination"})
            .find_all("a")[-1]["href"]
            .split("/")[-2]
        )

        for page in range(1, last_page + 1):
            if page > 1:
                response = requests.get(self.page_url.format(page=page))
                soup = BeautifulSoup(response.content, "html.parser")

            events = soup.find_all("li", {"itemscope": "itemscope"})
            for event in events:
                url = event["href"]
                if not self.is_event_in_db(url):
                    self.event_urls.append(url)

    @retry(stop=stop_after_attempt(3))
    def run_event_pages(self) -> None:
        run_event_urls = self.event_urls.copy()
        logging.info(f"Running {len(run_event_urls)} pages")
        for i, url in enumerate(run_event_urls):
            logging.info(f"{i+1}/{len(run_event_urls)}")

            response = requests.get(url)
            soup = BeautifulSoup(response.content, "html.parser")

            city, place = [
                s.strip()
                for s in soup.find(
                    "h2", {"class", "t-event__surtitle uppercase--md"}
                ).text.split(b"\xe2\x80\x94".decode("utf-8"))
            ]
            is_countryside = False if city == "Torino" else True

            title = soup.find("h1", {"class": "t-event__title condensed--xl"}).text
            subtitle = soup.find("p", {"class": "t-event__subtitle serif--md"}).text

            dates = soup.find_all("div", {"class": "dates__cell"})

            start_date, end_date = [
                datetime.datetime.strptime(
                    convert_italian_month(d.find("p", {"class": "dates__full"}).text),
                    "%d %B %Y",
                ).date()
                for d in dates
            ]

            opening_time = dates[0].find("p", {"class": "dates__time"}).text[5:]
            closing_time_temp = dates[1].find("p", {"class": "dates__time"}).text
            closing_time = (
                "24:00"
                if closing_time_temp == "fino a tarda notte"
                else closing_time_temp[5:]
            )
            is_during_day, is_during_night = self.get_timing_flags(
                opening_time, closing_time
            )

            contents = soup.find_all(
                "div",
                {
                    "class",
                    "content typography typography--dropcap-none base-section-col__content",
                },
            )
            text = contents[0].text.strip()
            address = contents[1].text.strip()[11:]

            description = "\n".join([title, subtitle, text])
            location = " - ".join([place, address, city])

            self.output.append(
                Event(
                    description=description,
                    is_vectorized=False,
                    # metadata
                    city=CityEnum.Torino,
                    start_date=start_date,
                    end_date=end_date,
                    is_closed_mon=False,
                    is_closed_tue=False,
                    is_closed_wed=False,
                    is_closed_thu=False,
                    is_closed_fri=False,
                    is_closed_sat=False,
                    is_closed_sun=False,
                    is_during_day=is_during_day,
                    is_during_night=is_during_night,
                    is_countryside=is_countryside,
                    is_for_children=False,
                    is_for_disabled=False,
                    is_for_animals=False,
                    # additional info
                    name=title,
                    location=location,
                    url=url,
                    price_level=None,
                )
            )
            self.event_urls.remove(url)

    def run(self) -> None:
        self.run_root_page()
        self.run_event_pages()


SCRAPER_SUPPORTED_SOURCES = {
    "guidatorino": GuidatorinoScraper,
    "lovelanghe": LovelangheScraper,
}


class Scraper:
    def __init__(self, identifier: str, db: Session) -> None:
        self.db = db
        self.set_scraper(identifier)

    def set_scraper(self, identifier: str) -> None:
        if identifier not in SCRAPER_SUPPORTED_SOURCES:
            raise Exception(f"Scraper with identifier {identifier} is not supported.")
        self.scraper = SCRAPER_SUPPORTED_SOURCES[identifier](db=self.db)

    def update_db(self) -> int:
        counter = 0
        for event in self.scraper.output:
            db_event = get_event(db=self.db, source=self.scraper.source, url=event.url)
            if db_event is None:
                db_event = register_event(
                    db=self.db, event_in=event, source=self.scraper.source
                )
                counter += 1

        self.db.commit()
        return counter

    def run(self) -> None:
        logging.info(f"Starting scraper for {self.scraper.identifier}.")
        self.scraper.run()
        num_inserted_events = self.update_db()
        logging.info(f"Inserted {num_inserted_events} new events.")
