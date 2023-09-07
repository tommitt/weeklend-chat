import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup


class BaseScraper:
    _closed_days_cols = [
        "is_closed_mon",
        "is_closed_tue",
        "is_closed_wed",
        "is_closed_thu",
        "is_closed_fri",
        "is_closed_sat",
        "is_closed_sun",
    ]

    _full_cols = (
        [
            "description",
            "city",
            "start_date",
            "end_date",
        ]
        + _closed_days_cols
        + [
            "is_during_day",
            "is_during_night",
            "location",
            "url",
            "opening_time",
            "closing_time",
        ]
    )

    def __init__(self) -> None:
        self.identifier = "base"
        self.df: pd.DataFrame = pd.DataFrame()

    def create_timing_flags(self) -> None:
        self.df["is_during_day"] = (
            self.df["opening_time"].str.split(":", expand=True)[0].astype(int) <= 18
        )
        self.df["is_during_night"] = (
            self.df["closing_time"].str.split(":", expand=True)[0].astype(int) >= 20
        )

    def save_db(self) -> None:
        # self.df["id"] = TODO
        self.df[self._full_cols].to_csv(f"data/{self.identifier}_db.csv", index=False)


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

    def run(self) -> None:
        print(f"Starting scraper for {self.identifier}")

        response = requests.get(self.root_url)
        soup = BeautifulSoup(response.content)

        output = {
            "title": [],
            "description": [],
            "start_date": [],
            "end_date": [],
            "city": [],
            "location": [],
            "url": [],
            "opening_time": [],
            "closing_time": [],
        }

        events = (
            soup.find("table", {"class": "events-table"}).find("tbody").find_all("tr")
        )
        n_events = len(events)

        for event in events:
            content = event.find("div", {"class", "eventlist-2"})
            sub_contents = content.find_all("p")

            output["url"].append(content.find("h3").find("a")["href"])
            output["title"].append(content.find("h3").find("a").text)

            dates = [
                datetime.datetime.strptime(d.replace(key, val), "%d-%m-%Y").date()
                for d in sub_contents[0]
                .find("span", {"class": "lista-data"})
                .text.split(" - ")
                for key, val in self._MONTHS_CONVERSION.items()
                if key in d
            ]
            output["start_date"].append(dates[0])
            output["end_date"].append(dates[0] if len(dates) == 1 else dates[1])

            timing = (
                sub_contents[0]
                .find("span", {"class": "lista-orario"})
                .text.strip("Orario:  ")
                .split(" - ")
            )
            output["opening_time"].append(timing[0])
            output["closing_time"].append(timing[1])

            city = sub_contents[1].find("span", {"class": "evento-citta"}).text
            address = sub_contents[1].find("span", {"class": "evento-indirizzo"}).text
            place = sub_contents[1].find("span", {"class": "lista-luogo"}).text
            location = (
                city
                if (city == place) and (city == address)
                else " - ".join([place, address, city])
            )
            output["city"].append(city)
            output["location"].append(location)

        for i in range(n_events):
            print(f"{i+1}/{n_events}")

            event_response = requests.get(output["url"][i])
            event_soup = BeautifulSoup(event_response.content, "html.parser")

            text_containers = event_soup.find("div", {"class": "testo"}).find_all("p")

            texts = [output["title"][i]]
            for t in text_containers:
                text = t.text
                if text == "\xa0":
                    pass
                elif text.startswith("Potete acquistare") or text.startswith(
                    "\xa0\nQuando"
                ):
                    break
                texts.append(text)

            output["description"].append("\n".join(texts))

        for col in self._closed_days_cols:
            output[col] = [False] * n_events
        output.pop("title", None)

        self.df = pd.DataFrame(output)
