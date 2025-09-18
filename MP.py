import yaml


class MP:
    """MP data."""

    def __init__(self, id: int, name: str, party: str, division: str) -> None:
        self.id = id
        self.name = name
        self.party = self._abbreviated_party_name(party)
        self.division = division

    def _abbreviated_party_name(self, long_name: str) -> str:
        with open("_data/parties.yml", "r") as f:
            parties = yaml.safe_load(f)

        for party in parties:
            if "long_name" in party and party["long_name"] == long_name:
                return party["name"]

        return long_name

    def __repr__(self) -> str:
        return f"MP({self.id}, {self.name}, {self.party}, {self.division})"

    def __str__(self) -> str:
        return self.name
