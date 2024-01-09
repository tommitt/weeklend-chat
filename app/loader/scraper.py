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
        self.event_urls: list[str] = []
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

    def run_root_page(self) -> None:
        raise NotImplementedError("Function not implemented for base class.")

    def run_event_page(self, url: str) -> Event:
        raise NotImplementedError("Function not implemented for base class.")

    @retry(stop=stop_after_attempt(3))
    def run_all_event_pages(self) -> None:
        run_event_urls = self.event_urls.copy()
        logging.info(f"Running {len(run_event_urls)} pages")
        for i, url in enumerate(run_event_urls):
            logging.info(f"{i+1}/{len(run_event_urls)}")

            try:
                event = self.run_event_page(url)
                self.output.append(event)

            except Exception as e:
                logging.info(
                    f"Failed to retrieve info from event at: {url}. Exception: {e}"
                )
                pass

            self.event_urls.remove(url)

    def run(self) -> None:
        self.run_root_page()
        self.run_all_event_pages()


class GuidatorinoScraper(BaseScraper):
    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.identifier: str = "guidatorino"
        self._root_url: str = "https://www.guidatorino.com/eventi-torino/"
        self._events_list: list[dict] = []

    def run_root_page(self) -> None:
        response = requests.get(self._root_url)
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

                dates = [
                    datetime.datetime.strptime(
                        convert_italian_month(d), "%d %m %Y"
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

                self._events_list.append(event_dict)

            except Exception as e:
                logging.info(f"Skipping event for exception: {e}")
                pass

        logging.info(f"Got {len(self._events_list)} new events to be scraped.")

    @retry(stop=stop_after_attempt(3))
    def run_all_event_pages(self) -> None:
        run_events_list = self._events_list.copy()
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
                    is_during_day=event_dict["is_during_day"],
                    is_during_night=event_dict["is_during_night"],
                    # additional info
                    name=event_dict["title"],
                    location=event_dict["location"],
                    url=event_dict["url"],
                )
            )
            self._events_list.remove(event_dict)


class LovelangheScraper(BaseScraper):
    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.identifier: str = "lovelanghe"
        self._root_url: str = "https://langhe.net/eventi/"
        self._page_url: str = "https://langhe.net/eventi/page/{page}/"

    def run_root_page(self) -> None:
        response = requests.get(self._root_url)
        soup = BeautifulSoup(response.content, "html.parser")

        last_page = int(
            soup.find("div", {"class": "pagination pagination--event grid__pagination"})
            .find_all("a")[-1]["href"]
            .split("/")[-2]
        )

        for page in range(1, last_page + 1):
            if page > 1:
                response = requests.get(self._page_url.format(page=page))
                soup = BeautifulSoup(response.content, "html.parser")

            events = soup.find_all("li", {"itemscope": "itemscope"})
            for event in events:
                url = event["href"]
                if not self.is_event_in_db(url):
                    self.event_urls.append(url)

    def run_event_page(self, url: str) -> Event:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        city, place = [
            s.strip()
            for s in soup.find(
                "h2", {"class", "t-event__surtitle uppercase--md"}
            ).text.split(b"\xe2\x80\x94".decode("utf-8"))
        ]

        title = soup.find("h1", {"class": "t-event__title condensed--xl"}).text
        subtitle = soup.find("p", {"class": "t-event__subtitle serif--md"}).text

        dates = soup.find_all("div", {"class": "dates__cell"})

        start_date, end_date = [
            datetime.datetime.strptime(
                convert_italian_month(d.find("p", {"class": "dates__full"}).text),
                "%d %m %Y",
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

        return Event(
            description=description,
            is_vectorized=False,
            # metadata
            city=CityEnum.Torino,
            start_date=start_date,
            end_date=end_date,
            is_during_day=is_during_day,
            is_during_night=is_during_night,
            # additional info
            name=title,
            location=location,
            url=url,
        )


class XceedScraper(BaseScraper):
    def __init__(self, db: Session) -> None:
        super().__init__(db=db)
        self.identifier: str = "xceed"
        self._ext_event_url: str = (
            "https://xceed.me/it/torino/event/{slug}--{legacy_id}"
        )
        self._api_root_url: str = "https://events.xceed.me/v1/"
        self._api_page_url: str = (
            self._api_root_url
            + "cities/torino/events/categories/all-events/events?offset={offset}"
        )
        self._api_event_url: str = self._api_root_url + "events/{legacy_id}?lang=it"
        self._api_club_url: str = self._api_root_url + "clubs/{club_id}"
        self._api_lineup_url: str = self._api_root_url + "events/{event_id}/line-up"

    def run_root_page(self) -> None:
        offset = 0
        while True:
            response = requests.get(self._api_page_url.format(offset=offset))
            response_json = response.json()

            if len(response_json["data"]) == 0:
                break

            for event_data in response_json["data"]:
                event_url = self._api_event_url.format(legacy_id=event_data["legacyId"])

                ext_url = self._ext_event_url.format(
                    slug=event_data["slug"], legacy_id=event_data["legacyId"]
                )
                if not self.is_event_in_db(ext_url):
                    self.event_urls.append(event_url)

            offset += 10

    def run_event_page(self, url: str) -> Event:
        response = requests.get(url)
        data = response.json()["data"]

        ext_url = self._ext_event_url.format(
            slug=data["slug"], legacy_id=data["legacyId"]
        )

        start_dt = datetime.datetime.fromtimestamp(data["startingTime"])
        end_dt = datetime.datetime.fromtimestamp(data["endingTime"])
        start_date = start_dt.date()
        end_date = start_date

        club_name = data["venue"]["name"]
        club_response = requests.get(
            self._api_club_url.format(club_id=data["venue"]["id"])
        )
        club_data = club_response.json()["data"]
        club_address = club_data["address"]
        location_list = [club_name, club_address]
        if "Torino" not in club_address:
            location_list.append("Torino")
        location = " | ".join(location_list)

        lineup_response = requests.get(self._api_lineup_url.format(event_id=data["id"]))
        lineup_data = lineup_response.json()["data"]
        lineup_names = ", ".join([l["name"] for l in lineup_data])

        name = data["name"]
        genres = ", ".join([g["name"] for g in data["musicGenres"]])
        description = "\n".join(
            [
                name,
                "Evento in discoteca.",
                f"Genere musicale: {genres}" if len(genres) > 0 else "",
                f"Lineup artisti: {lineup_names}" if len(lineup_names) > 0 else "",
                f"Orario dalle {start_dt.hour} alle {end_dt.hour}.",
                data["about"],
                club_data["about"],
            ]
        )

        return Event(
            description=description,
            is_vectorized=False,
            city=CityEnum.Torino,
            start_date=start_date,
            end_date=end_date,
            is_during_day=False,
            is_during_night=True,
            name=name,
            location=location,
            url=ext_url,
        )


SCRAPER_SUPPORTED_SOURCES = {
    "guidatorino": GuidatorinoScraper,
    "lovelanghe": LovelangheScraper,
    "xceed": XceedScraper,
}


class Scraper:
    def __init__(self, identifier: str, db: Session) -> None:
        self.db = db
        self.set_scraper(identifier)

    def set_scraper(self, identifier: str) -> None:
        if identifier not in SCRAPER_SUPPORTED_SOURCES:
            raise Exception(f"Scraper with identifier {identifier} is not supported.")
        self.scraper: BaseScraper = SCRAPER_SUPPORTED_SOURCES[identifier](db=self.db)

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
