"""Scrapes data from aph.gov.au for current bills and outputs to YAML."""

import requests
from bs4 import BeautifulSoup
from typing import List
from MP import MP
from Bill import Bill


PENDING_BILLS_URL = "https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_before_Parliament?ps=100&page=1"
PASSED_BILLS_URL = "https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Assented_Bills_of_the_current_Parliament?ps=100&page=1"
FAILED_BILLS_URL = "https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_not_passed_current_Parliament?ps=100&page=1"

REPRESENTATIVES_URL = "http://data.openaustralia.org.au/members/representatives.xml"
SENATORS_URL = "http://data.openaustralia.org.au/members/senators.xml"
PEOPLE_URL = "http://data.openaustralia.org.au/members/people.xml"


def get_bills(bills_url: str) -> List[Bill]:
    """Get bills from bills URL."""

    # Get HTML from pending bills and parse it
    response = requests.get(bills_url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Get bill URLs
    bill_link_tags = soup.find_all(
        "a",
        attrs={
            "id": lambda L: L and L.startswith("main_0_content_0_lvResults_hlTitle_")
        },
    )
    bills = [
        Bill(bill_link_tag["href"].split("bId=")[1], mps)
        for bill_link_tag in bill_link_tags
    ]

    # Scrape additional pages
    next_page = soup.find("a", attrs={"title": "Next page"})
    if next_page:
        url_base, page_number = bills_url.split("page=")
        next_url = url_base + "page=" + str(int(page_number) + 1)

        return bills + get_bills(next_url)

    return bills


# Get raw data
representative_response = requests.get(REPRESENTATIVES_URL)
senator_response = requests.get(SENATORS_URL)
members = BeautifulSoup(representative_response.text, "xml").find_all(
    "member"
) + BeautifulSoup(senator_response.text, "xml").find_all("member")

people_response = requests.get(PEOPLE_URL)
people = BeautifulSoup(people_response.text, "xml").find_all("person")

# Get MP data
mps = []
for person in people:
    offices = person.find_all("office")
    offices = [
        office
        for office in offices
        if "uk.org.publicwhip/member/" in office["id"]
        or "uk.org.publicwhip/lord/" in office["id"]
    ]  # Filter out ministries
    office_id = None

    for office in offices:  # Get current office if they have one
        if office.has_attr("current") and office["current"] == "yes":
            office_id = office["id"]
            break
    else:  # Use last office otherwise
        office_ids = [office["id"] for office in offices]
        office_id = max(office_ids, key=lambda id: int(id.split("/")[-1]))

    # Get party
    party = [member["party"] for member in members if member["id"] == office_id][0]

    # Add MP
    mps.append(
        MP(
            person["id"].split("/")[-1],
            person["latestname"],
            party,
        )
    )

# Create YAML file to capture all this information
with open("_data/bills.yaml", "w") as f:
    print("Downloading pending bills")
    f.write("pending:\n")
    for bill in get_bills(PENDING_BILLS_URL):
        f.write(bill.yaml())

    print("Downloading passed bills")
    f.write("passed:\n")
    for bill in get_bills(PASSED_BILLS_URL):
        f.write(bill.yaml())

    print("Downloading failed bills")
    f.write("failed:\n")
    for bill in get_bills(FAILED_BILLS_URL):
        f.write(bill.yaml())
