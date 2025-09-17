import json
import re
import time
from datetime import datetime
from typing import List, Optional

import requests
import yaml
from bs4 import BeautifulSoup
from termcolor import colored

from MP import MP
from SystemID import SystemID

_DOWNLOAD_RETRIES = 10
_DOWNLOAD_DELAY_SECONDS = 30


class Bill:
    """Bill data."""

    def __init__(self, id: str, mps: List[MP]) -> None:
        self.id = id
        print(f"Starting bill\t{self._colored_id()}")
        self._mps = mps
        self._ruling_party = self._get_ruling_party()
        self._soup = BeautifulSoup(
            self._download_page(
                f"https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_Search_Results/Result?bId={self.id}"
            ),
            "html.parser",
        )
        self.minister_name = self._get_minister_name()
        print(f"Loaded bill \t{self._colored_id()}: {self._get_title()}\n")

    def _get_ruling_party(self) -> str:
        party_members = dict()
        for mp in self._mps:
            if mp.party not in party_members:
                party_members[mp.party] = 0

            party_members[mp.party] += 1

        return max(party_members, key=party_members.get)

    def _colored_id(self) -> str:
        if self.id.startswith("r"):
            return colored(self.id, "green")

        return colored(self.id, "red")

    def _download_page(self, url: str) -> str:
        for _ in range(_DOWNLOAD_RETRIES):
            response = requests.get(
                url,
                headers={
                    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
                },
            )

            if response.status_code // 100 == 2:
                break

            print(
                f"Retrying download of {url}\t{colored(f'error {response.status_code}', 'red')}"
            )
            time.sleep(_DOWNLOAD_DELAY_SECONDS)
        else:
            raise Exception(f"Failed to download {url}")

        return response.text

    def _get_title(self) -> str:
        return self._soup.find("meta", {"property": "og:title"})["content"]

    def _get_status(self) -> str:
        return (
            self._soup.find("dt", string="Status").find_next_sibling("dd").text.strip()
        )

    def _get_type(self) -> str:
        return self._soup.find("dt", string="Type").find_next_sibling("dd").text.strip()

    def _get_portfolio(self) -> Optional[str]:
        try:
            return (
                self._soup.find("dt", string="Portfolio")
                .find_next_sibling("dd")
                .text.strip()
            )
        except AttributeError:
            return None

    def _get_second_reading_hansard_url(self) -> Optional[str]:
        try:
            return (
                self._soup.find("ul", {"class": "speech-transcripts"})
                .find_all("li")[1]
                .find("a")["href"]
            )
        except (AttributeError, IndexError):
            return None

    def _get_minister_name(self) -> str:
        if self._get_portfolio() is None:
            return None

        # Get minister's speech URL
        minister_second_reading_url = self._get_second_reading_hansard_url()

        if minister_second_reading_url is None:
            return None

        name_text = None
        system_id = SystemID(minister_second_reading_url)

        while name_text is None:
            # Get aph.gov.au JSON URL
            minister_second_reading_url = system_id.json_url()

            # Get speech JSON
            json_str = self._download_page(minister_second_reading_url)
            speech_json = json.loads(json_str)

            # Ensure the speech is the minister's second reading
            if speech_json.get("Title") != "":
                system_id.progress()
                continue

            # Get MP name
            name_text = speech_json.get("Speaker")

        # Format name
        name_parts = (
            name_text.strip().replace(" MP", "").replace("Sen ", "").split(", ")
        )
        formatted_name = f"{name_parts[1]} {name_parts[0]}".title()
        formatted_name = formatted_name.split(" ")
        formatted_name = formatted_name[0] + " " + formatted_name[-1]
        print(f"Got minister's name\t{colored(formatted_name, 'yellow')}")
        return formatted_name

    def _get_originating_house(self) -> str:
        return (
            self._soup.find("dt", string="Originating house")
            .find_next_sibling("dd")
            .text.strip()
        )

    def _get_summary(self) -> str:
        try:
            return (
                self._soup.find("div", {"id": "main_0_summaryPanel"})
                .findChildren()[1]
                .text.strip()
            )
        except AttributeError:
            return None

    def _get_sponsor_name(self) -> Optional[str]:
        try:
            sponsor_tag = self._soup.find("dt", string="Sponsor(s)").find_next_sibling(
                "dd"
            )
            text = ""
            for content in sponsor_tag.contents:
                if content.name == "br":
                    break
                if isinstance(content, str):
                    text += content

            name_parts = text.strip().replace("Sen ", "").split(", ")
        except AttributeError:
            return None

        return f"{name_parts[1]} {name_parts[0]}".title()

    def _get_introducer_division(self, name: str) -> Optional[str]:
        if name is None:
            return None

        for mp in self._mps:
            if mp.name.lower() == name.lower():
                return mp.division

        return None

    def _get_introducer_party(
        self, name: str, is_minister: bool = False
    ) -> Optional[str]:
        # If introducer name is not found, assume ruling party for Government bills
        if name is None:
            if self._get_type() == "Government" and is_minister:
                return self._ruling_party

            return None

        # If introducer name is found, get their party
        for mp in self._mps:
            if mp.name.lower() == name.lower():
                if mp.party == "SPK":  # Special case for the Speaker
                    return self._ruling_party

                return mp.party

        # If introducer name is known but their party is unknown, assume ruling party for Government bills
        if self._get_type() == "Government" and is_minister:
            return self._ruling_party

        return None

    def _get_introducer_id(self, name: str) -> Optional[int]:
        if name is None:
            return None

        for mp in self._mps:
            if mp.name.lower() == name.lower():
                return mp.id

        return None

    def _get_pdf_url(self) -> str:
        table = self._soup.find("h3", string="Text of bill").find_next_sibling("table")
        row = table.find_all("tr")[-1]
        return row.find_all("td")[1].find_all("a")[1]["href"]

    def _get_last_updated(self) -> str:
        (day, month_word, year) = (
            self._soup.find("div", {"id": "main_0_mainDiv"})
            .find_all("table")[-1]
            .find("tbody")
            .find_all("tr")[-1]
            .find_all("td")[-1]
            .text.strip()
            .split(" ")
        )
        month = datetime.strptime(month_word, "%b").month
        return f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"

    def yaml(self) -> str:
        """Convert bill to YAML."""

        # Add null representer
        yaml.add_representer(
            type(None), lambda _, x: yaml.ScalarNode("tag:yaml.org,2002:null", "null")
        )

        # Add timestamp representer
        yaml.add_representer(
            str,
            lambda _, x: yaml.ScalarNode(
                "tag:yaml.org,2002:str"
                if not re.compile(r"^\d{4}-\d{2}-\d{2}$").match(x)
                else "tag:yaml.org,2002:timestamp",
                x,
            ),
        )

        # Construct YAML object
        data = [
            {
                "bill_id": self.id,
                "title": self._get_title(),
                "status": self._get_status(),
                "type": self._get_type(),
                "portfolio": self._get_portfolio(),
                "originating_house": self._get_originating_house(),
                "summary": self._get_summary(),
                "sponsor_name": self._get_sponsor_name(),
                "sponsor_party": self._get_introducer_party(self._get_sponsor_name()),
                "sponsor_id": self._get_introducer_id(self._get_sponsor_name()),
                "sponsor_division": self._get_introducer_division(
                    self._get_sponsor_name()
                ),
                "minister_name": self.minister_name,
                "minister_party": self._get_introducer_party(self.minister_name, True),
                "minister_id": self._get_introducer_id(self.minister_name),
                "minister_division": self._get_introducer_division(self.minister_name),
                "pdf_url": self._get_pdf_url(),
                "last_updated": self._get_last_updated(),
                "second_reading_hansard_url": self._get_second_reading_hansard_url(),
            }
        ]

        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def __repr__(self) -> str:
        return f"{self.id}: {self._get_title()}"

    def __str__(self) -> str:
        return f"{self.id}: {self._get_title()}"
