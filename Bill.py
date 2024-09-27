import requests
import time
from bs4 import BeautifulSoup
from typing import List
import urllib.parse
from requests_html import HTMLSession
from termcolor import colored


from MP import MP


class Bill:
    """Bill data."""

    def __init__(self, id: str, mps: List[MP]) -> None:
        self.id = id
        print(f"Downloading bill\t{self._colored_id()}")
        self.mps = mps
        self.soup = self._parse_webpage(
            f"https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_Search_Results/Result?bId={id}"
        )
        self.minister_name = self._get_minister_name()
        print(f"Downloaded bill \t{self._colored_id()}: {self._get_title()}\n")

    def _colored_id(self) -> str:
        if self.id.startswith("r"):
            return colored(self.id, "green")

        return colored(self.id, "red")

    def _parse_webpage(self, url: str) -> BeautifulSoup:
        download_worked = False
        while not download_worked:
            response = requests.get(url)
            download_worked = response.status_code // 100 == 2

            if not download_worked:
                print(
                    f"Retrying download\t{colored(f'error {response.status_code}', 'red')}"
                )
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

    def _get_minister_name(self) -> str:
        if self._get_portfolio() is None:
            return None

        # Get minister's speech URL
        minister_second_reading_url = None
        try:
            minister_second_reading_url = (
                self.soup.find("ul", {"class": "speech-transcripts"})
                .find_all("li")[1]
                .find("a")["href"]
            )
        except AttributeError:
            return None

        # Get query ID
        query_id = (
            urllib.parse.unquote(minister_second_reading_url.split("query=Id")[1])
            .replace(":", "")
            .replace('"', "")
        )

        # Get Hansard page
        session = HTMLSession()
        response = session.get(
            f"https://www.aph.gov.au/Parliamentary_Business/Hansard/Hansard_Display?bid={query_id}"
        )
        render_success = False
        while not render_success:
            render_success = True
            try:
                response.html.render(sleep=1)
            except TimeoutError:
                render_success = False

        hansard_soup = BeautifulSoup(response.html.html, "html.parser")
        session.close()

        # Get MP name
        name_text = hansard_soup.find("span", {"data-bind": "text: speaker"}).text
        if name_text == "":
            return None
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

    def _get_introducer_party(self, name) -> str:
        if name is None:
            return None

        for mp in self.mps:
            if mp.name.lower() == name.lower():
                return mp.party

        return None

    def _get_introducer_id(self, name) -> int:
        if name is None:
            return None

        for mp in self.mps:
            if mp.name.lower() == name.lower():
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
    sponsor_party: \"{self._get_introducer_party(self._get_sponsor_name())}\"
    sponsor_id: \"{self._get_introducer_id(self._get_sponsor_name())}\"
    minister_name: \"{self.minister_name}\"
    minister_party: \"{self._get_introducer_party(self.minister_name)}\"
    minister_id: \"{self._get_introducer_id(self.minister_name)}\" 
    pdf_url: \"{self._get_pdf_url()}\"
"""

    def __repr__(self) -> str:
        return f"{self.id}: {self._get_title()}"

    def __str__(self) -> str:
        return f"{self.id}: {self._get_title()}"
