import json
import re
import time
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from termcolor import colored

from MP import MP

_DOWNLOAD_RETRIES = 10
_DOWNLOAD_DELAY_SECONDS = 30


class Bill:
    """Bill data."""

    def __init__(
        self, id: str, mps: List[MP], existing_bill: Optional[dict] = None
    ) -> None:
        self.id = id
        print(f"Starting bill\t{self._colored_id()}")
        self.existing_bill = existing_bill
        self.mps = mps
        self._ruling_party = self._get_ruling_party()
        self.soup = self._parse_webpage(
            f"https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_Search_Results/Result?bId={id}"
        )
        self.minister_name = self._get_minister_name()
        print(f"Loaded bill \t{self._colored_id()}: {self._get_title()}\n")

    def _get_ruling_party(self) -> str:
        party_members = dict()
        for mp in self.mps:
            if mp.party not in party_members:
                party_members[mp.party] = 0

            party_members[mp.party] += 1

        return max(party_members, key=party_members.get)

    def _colored_id(self) -> str:
        if self.id.startswith("r"):
            return colored(self.id, "green")

        return colored(self.id, "red")

    def _existing_bill_is_sufficient(self) -> bool:
        if self.existing_bill is None:
            print(colored("No existing bill", "yellow"))
            return False

        # Check if bill's status indicates it is in progress
        if self.existing_bill["status"] not in ["Act", "Not Proceeding"]:
            print(
                colored(
                    f"Updating bill data due to status {self.existing_bill['status']}",
                    "yellow",
                )
            )
            return False

        # Check if all required fields are present
        required_fields = [
            "bill_id",
            "title",
            "status",
            "type",
            "originating_house",
            "summary",
            "last_updated",
            "second_reading_hansard_url",
        ]
        if self.existing_bill["type"] == "Private":
            required_fields.extend(
                ["sponsor_name", "sponsor_party", "sponsor_id", "sponsor_division"]
            )
        else:
            required_fields.extend(
                [
                    "minister_name",
                    "minister_party",
                    "minister_id",
                    "portfolio",
                    "minister_division",
                ]
            )

        for required_field in required_fields:
            if (
                required_field not in self.existing_bill
                or self.existing_bill[required_field] is None
            ):
                print(
                    colored(
                        f"Updating bill data due to missing {required_field}", "yellow"
                    )
                )
                return False

        print(colored("Existing bill data is sufficient", "yellow"))
        return True

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

    def _parse_webpage(self, url: str) -> Optional[BeautifulSoup]:
        # Check if bill has any need to be updated
        if self._existing_bill_is_sufficient():
            return None

        # Download bill page
        return BeautifulSoup(self._download_page(url), "html.parser")

    def _get_title(self) -> str:
        if self.soup is None:
            return self.existing_bill["title"]

        return self.soup.find("meta", {"property": "og:title"})["content"]

    def _get_status(self) -> str:
        if self.soup is None:
            return self.existing_bill["status"]

        return (
            self.soup.find("dt", string="Status").find_next_sibling("dd").text.strip()
        )

    def _get_type(self) -> str:
        if self.soup is None:
            return self.existing_bill["type"]

        return self.soup.find("dt", string="Type").find_next_sibling("dd").text.strip()

    def _get_portfolio(self) -> str:
        if self.soup is None:
            return self.existing_bill["portfolio"]

        try:
            return (
                self.soup.find("dt", string="Portfolio")
                .find_next_sibling("dd")
                .text.strip()
            )
        except AttributeError:
            return None

    def _get_second_reading_hansard_url(self) -> str:
        if self.soup is None:
            return self.existing_bill["second_reading_hansard_url"]

        try:
            return (
                self.soup.find("ul", {"class": "speech-transcripts"})
                .find_all("li")[1]
                .find("a")["href"]
            )
        except (AttributeError, IndexError):
            return None

    def _get_minister_name(self) -> str:
        if self._get_portfolio() is None:
            return None
        elif (
            self.existing_bill is not None
            and self.existing_bill["minister_name"] is not None
        ):
            return self.existing_bill["minister_name"]

        # Get minister's speech URL
        minister_second_reading_url = self._get_second_reading_hansard_url()

        if minister_second_reading_url is None:
            return None

        # Convert parlinfo URL to aph.gov.au JSON URL
        minister_second_reading_url = re.sub(
            r"https://parlinfo.aph.gov.au/parlInfo/search/display/display.w3p;query=Id%3A%22(\w+)%2F(\w+)%2F(\d+)%2F(\d+)%22",
            r"https://www.aph.gov.au/api/hansard/transcript?id=\1%2F\2%2F\3%2F\4",
            minister_second_reading_url,
        )

        # Get speech JSON
        json_str = self._download_page(minister_second_reading_url)
        speech_json = json.loads(json_str)

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
        if self.soup is None:
            return self.existing_bill["originating_house"]

        return (
            self.soup.find("dt", string="Originating house")
            .find_next_sibling("dd")
            .text.strip()
        )

    def _get_summary(self) -> str:
        if self.soup is None:
            return self.existing_bill["summary"]

        try:
            return (
                self.soup.find("div", {"id": "main_0_summaryPanel"})
                .findChildren()[1]
                .text.strip()
            )
        except AttributeError:
            return None

    def _get_sponsor_name(self) -> str:
        if self.soup is None:
            return self.existing_bill["sponsor_name"]

        try:
            sponsor_tag = self.soup.find("dt", string="Sponsor(s)").find_next_sibling(
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

    def _get_introducer_division(self, name: str) -> str:
        if name is None:
            return None

        for mp in self.mps:
            if mp.name.lower() == name.lower():
                return mp.division

        return None

    def _get_introducer_party(self, name: str, is_minister: bool = False) -> str:
        # If introducer name is not found, assume ruling party for Government bills
        if name is None:
            if self._get_type() == "Government" and is_minister:
                return self._ruling_party

            return None

        # If introducer name is found, get their party
        for mp in self.mps:
            if mp.name.lower() == name.lower():
                if mp.party == "SPK":  # Special case for the Speaker
                    return self._ruling_party

                return mp.party

        # If introducer name is known but their party is unknown, assume ruling party for Government bills
        if self._get_type() == "Government" and is_minister:
            return self._ruling_party

        return None

    def _get_introducer_id(self, name: str) -> int:
        if name is None:
            return None

        for mp in self.mps:
            if mp.name.lower() == name.lower():
                return mp.id

        return None

    def _get_pdf_url(self) -> str:
        if self.soup is None:
            return self.existing_bill["pdf_url"]

        table = self.soup.find("h3", string="Text of bill").find_next_sibling("table")
        row = table.find_all("tr")[-1]
        return row.find_all("td")[1].find_all("a")[1]["href"]

    def _get_last_updated(self) -> str:
        if self.soup is None:
            return self.existing_bill["last_updated"]

        (day, month_word, year) = (
            self.soup.find("div", {"id": "main_0_mainDiv"})
            .find_all("table")[-1]
            .find("tbody")
            .find_all("tr")[-1]
            .find_all("td")[-1]
            .text.strip()
            .split(" ")
        )
        month = datetime.strptime(month_word, "%b").month
        return f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"

    def _yaml_value_wrapper(self, value, yaml_string: bool = True) -> str:
        if value is None:
            return "null"
        elif yaml_string:
            value = (
                value.replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
            )
            return f'"{value}"'

        return value

    def yaml(self) -> str:
        """Convert bill to YAML."""
        return f"""\
  - bill_id: {self._yaml_value_wrapper(self.id)}
    title: {self._yaml_value_wrapper(self._get_title())}
    status: {self._yaml_value_wrapper(self._get_status())}
    type: {self._yaml_value_wrapper(self._get_type())}
    portfolio: {self._yaml_value_wrapper(self._get_portfolio())}
    originating_house: {self._yaml_value_wrapper(self._get_originating_house())}
    summary: {self._yaml_value_wrapper(self._get_summary())}
    sponsor_name: {self._yaml_value_wrapper(self._get_sponsor_name())}
    sponsor_party: {self._yaml_value_wrapper(self._get_introducer_party(self._get_sponsor_name()))}
    sponsor_id: {self._yaml_value_wrapper(self._get_introducer_id(self._get_sponsor_name()))}
    sponsor_division: {self._yaml_value_wrapper(self._get_introducer_division(self._get_sponsor_name()))}
    minister_name: {self._yaml_value_wrapper(self.minister_name)}
    minister_party: {self._yaml_value_wrapper(self._get_introducer_party(self.minister_name, True))}
    minister_id: {self._yaml_value_wrapper(self._get_introducer_id(self.minister_name))}
    minister_division: {self._yaml_value_wrapper(self._get_introducer_division(self.minister_name))}
    pdf_url: {self._yaml_value_wrapper(self._get_pdf_url())}
    last_updated: {self._yaml_value_wrapper(self._get_last_updated(), False)}
    second_reading_hansard_url: {self._yaml_value_wrapper(self._get_second_reading_hansard_url())}
"""

    def __repr__(self) -> str:
        return f"{self.id}: {self._get_title()}"

    def __str__(self) -> str:
        return f"{self.id}: {self._get_title()}"
