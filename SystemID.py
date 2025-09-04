import re


class SystemID:
    def __init__(self, parl_info_url: str):
        self._parts = list(
            re.search(
                r"https://parlinfo\.aph\.gov\.au/parlInfo/search/display/display\.w3p;query=Id%3A%22(\w+)%2F(\w+)%2F(\d+)%2F(\d+)%22",
                parl_info_url,
            ).groups()
        )
        self._parts[-1] = int(self._parts[-1])

    def json_url(self):
        return f"https://www.aph.gov.au/api/hansard/transcript?id={self._parts[0]}/{self._parts[1]}/{self._parts[2]}/{str(self._parts[3]).zfill(4)}"

    def progress(self):
        self._parts[-1] += 1
