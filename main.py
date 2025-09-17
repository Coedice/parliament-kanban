"""Scrapes data from aph.gov.au for current bills and outputs to YAML."""

import os
from typing import List

import requests
from bs4 import BeautifulSoup
from termcolor import colored

from Bill import Bill
from MP import MP

SECTIONS = [
    (
        "pending",
        "https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_before_Parliament?ps=100&page=1",
    ),
    (
        "passed",
        "https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Assented_Bills_of_the_current_Parliament?ps=100&page=1",
    ),
    (
        "failed",
        "https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_not_passed_current_Parliament?ps=100&page=1",
    ),
]

REPRESENTATIVES_URL = "http://data.openaustralia.org.au/members/representatives.xml"
SENATORS_URL = "http://data.openaustralia.org.au/members/senators.xml"
PEOPLE_URL = "http://data.openaustralia.org.au/members/people.xml"


def get_bill_ids(section_name: str, bills_url: str, ids: List[str] = []) -> List[str]:
    """Get bill IDs from bills URL."""

    # Get HTML from pending bills and parse it
    response = requests.get(
        bills_url,
        headers={
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        },
    )
    soup = BeautifulSoup(response.text, "html.parser")

    # Get bill IDs
    bill_link_tags = soup.find_all(
        "a",
        attrs={
            "id": lambda L: L and L.startswith("main_0_content_0_lvResults_hlTitle_")
        },
    )
    bill_ids = [
        bill_link_tag["href"].split("bId=")[1] for bill_link_tag in bill_link_tags
    ]

    # Scrape any additional pages
    next_page = soup.find("a", attrs={"title": "Next page"})
    if next_page:
        url_base, page_number = bills_url.split("page=")
        next_url = url_base + "page=" + str(int(page_number) + 1)
        return get_bill_ids(section_name, next_url, ids=ids + bill_ids)

    # Remove any duplicates and sort
    bill_ids = sorted(list(set(bill_ids)))

    return bill_ids


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

    # Get division
    division = [member["division"] for member in members if member["id"] == office_id][
        0
    ]

    # Add MP
    mps.append(
        MP(
            person["id"].split("/")[-1],
            person["latestname"],
            party,
            division,
        )
    )

# Create YAML file to capture all this information
if os.path.exists("_data/bills.yml.tmp"):
    os.remove("_data/bills.yml.tmp")

for section_name, url in SECTIONS:
    print(
        colored(
            f"\nDownloading {section_name.capitalize()} bills",
            "blue",
            attrs=["underline"],
        )
    )
    with open("_data/bills.yml.tmp", "a") as f:
        f.write(f"{section_name}:\n")

    # Download and write bills
    for bill_id in get_bill_ids(section_name, url):
        new_bill = Bill(bill_id, mps)
        with open("_data/bills.yml.tmp", "a") as f:
            f.write(new_bill.yaml())

os.rename("_data/bills.yml.tmp", "_data/bills.yml")
