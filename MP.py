class MP:
    """MP data."""

    SHORT_NAMES = {
        "Liberal Party": "Liberal",
        "Australian Labor Party": "Labor",
        "Australian Greens": "Greens",
        "National Party": "National",
        "Pauline Hanson's One Nation Party": "One Nation",
    }

    def __init__(self, id: int, name: str, party: str) -> None:
        self.id = id
        self.name = name
        self.party = self._abbreviated_party_name(party)

    def _abbreviated_party_name(self, long_name: str) -> str:
        if long_name in self.SHORT_NAMES:
            return self.SHORT_NAMES[long_name]
        return long_name

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name
