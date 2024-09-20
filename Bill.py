import requests
import time
from bs4 import BeautifulSoup
from typing import List

from MP import MP


class Bill:
    """Bill data."""

    def __init__(self, id: str, mps: List[MP]) -> None:
        self.id = id
        self.mps = mps
        self.soup = self._parse_webpage(
            f"https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_Search_Results/Result?bId={id}"
        )
        print("Downloaded bill", self)

    def _parse_webpage(self, url: str) -> BeautifulSoup:
        download_worked = False
        while not download_worked:
            response = requests.get(url)
            download_worked = response.status_code // 100 == 2

            if not download_worked:
                print("Download failed, retrying in 20 seconds")
                time.sleep(20)

        return BeautifulSoup(response.text, "html.parser")

    def _get_title(self) -> str:
        return self.soup.find("meta", {"property": "og:title"})["content"]

    def _get_status(self) -> str:
        return (
            self.soup.find("dt", string="Status").find_next_sibling("dd").text.strip()
        )

    def _get_type(self) -> str:
        return self.soup.find("dt", string="Type").find_next_sibling("dd").text.strip()

    def _get_portfolio(self) -> str:
        try:
            return (
                self.soup.find("dt", string="Portfolio")
                .find_next_sibling("dd")
                .text.strip()
            )
        except AttributeError:
            return None

    def _get_originating_house(self) -> str:
        return (
            self.soup.find("dt", string="Originating house")
            .find_next_sibling("dd")
            .text.strip()
        )

    def _get_summary(self) -> str:
        try:
            return (
                self.soup.find("div", {"id": "main_0_summaryPanel"})
                .findChildren()[1]
                .text.strip()
            )
        except AttributeError:
            return None

    def _get_sponsor_name(self) -> str:
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

    def _get_sponsor_party(self) -> str:
        if self._get_sponsor_name() is None:
            return None

        for mp in self.mps:
            if mp.name.lower() == self._get_sponsor_name().lower():
                return mp.party

        return None

    def _get_sponsor_id(self) -> int:
        if self._get_sponsor_name() is None:
            return None

        for mp in self.mps:
            if mp.name.lower() == self._get_sponsor_name().lower():
                return mp.id

        return None

    def _get_pdf_url(self) -> str:
        table = self.soup.find("h3", string="Text of bill").find_next_sibling("table")
        row = table.find_all("tr")[-1]
        return row.find_all("td")[1].find_all("a")[1]["href"]

    def yaml(self) -> str:
        """Convert bill to YAML."""
        return f"""\
  - bill_id: \"{self.id}\"
    title: \"{self._get_title()}\"
    status: \"{self._get_status()}\"
    type: \"{self._get_type()}\"
    portfolio: \"{self._get_portfolio()}\"
    originating_house: \"{self._get_originating_house()}\"
    summary: \"{self._get_summary()}\"
    sponsor_name: \"{self._get_sponsor_name()}\"
    sponsor_party: \"{self._get_sponsor_party()}\"
    sponsor_id: \"{self._get_sponsor_id()}\"
    pdf_url: \"{self._get_pdf_url()}\"
"""

    def __repr__(self) -> str:
        return f"{self.id}: {self._get_title()}"

    def __str__(self) -> str:
        return f"{self.id}: {self._get_title()}"
