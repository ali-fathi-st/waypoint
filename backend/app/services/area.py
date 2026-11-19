"""
Is a job in your area? Used to skip far-away postings when collecting, and by
the match score to tell "remote, open to you" from "remote, US only".

Your area comes from the locations on your profile, e.g. "Edmonton, AB":
  * your cities        Edmonton
  * your provinces     AB (Alberta)
  * your countries     Canada (from the province code, or "Canada" itself)

A job is in your area when it's in one of your cities or provinces, or it's
remote and open to your country. If your profile has no locations, every job
counts. frontend/js/lib/area.js has the same rules for the website's sample
mode; tests check they agree.
"""

import re
from functools import lru_cache

PROVINCES = {
    "ab": "alberta", "bc": "british columbia", "mb": "manitoba", "nb": "new brunswick",
    "nl": "newfoundland", "ns": "nova scotia", "nt": "northwest territories", "nu": "nunavut",
    "on": "ontario", "pe": "prince edward island", "qc": "quebec", "sk": "saskatchewan", "yt": "yukon",
}  # fmt: skip
US_STATES = (
    "al ak az ar ca co ct de fl ga hi id il in ia ks ky la me md ma mi mn ms mo mt ne nv nh nj nm ny nc nd oh ok "
    "or pa ri sc sd tn tx ut vt va wa wv wi wy dc"
).split()

# Words that name a country or region in a job's location. "north america" counts for both.
COUNTRIES = {
    "canada": r"canada|canadian",
    "united states": r"united states|\busa\b|\bu\.s\.|\bus\b|\bamerica\b|bay area|san francisco|new york|\bnyc\b|"
    r"seattle|boston|chicago|austin|los angeles|denver|atlanta|miami|texas|california|washington,? d\.?c",
    "united kingdom": r"united kingdom|\buk\b|england|scotland|wales",
    "europe": r"europe|\bemea\b|\beu\b",
    "ireland": r"ireland", "germany": r"germany", "france": r"france", "spain": r"spain",
    "portugal": r"portugal", "netherlands": r"netherlands", "poland": r"poland", "india": r"india",
    "asia": r"\bapac\b|\basia\b|singapore|japan|philippines", "australia": r"australia|new zealand",
    "latin america": r"latam|latin america|brazil|mexico|argentina|colombia", "israel": r"israel",
}  # fmt: skip
OPEN_TO_ALL = r"anywhere|worldwide|global|international"


def _lower(text: str | None) -> str:
    return (text or "").lower()


def _city(location: str) -> str:
    return location.split(",")[0].strip().lower()


def user_area(locations: list[str]) -> dict:
    """{'cities': {...}, 'provinces': {...}, 'countries': {...}} from the profile's locations."""
    return _user_area(tuple(locations))


@lru_cache(maxsize=64)
def _user_area(locations: tuple[str, ...]) -> dict:
    cities, provinces, countries = set(), set(), set()
    for loc in locations:
        text = _lower(loc)
        cities.add(_city(loc))
        for code, name in PROVINCES.items():
            if re.search(rf",\s*{code}\b", text) or name in text:
                provinces.add(code)
                countries.add("canada")
        if any(re.search(rf",\s*{code}\b", text) for code in US_STATES if code not in PROVINCES):
            countries.add("united states")
        for country, pattern in COUNTRIES.items():
            if re.search(pattern, text):
                countries.add(country)
    if re.search(r"north america", " ".join(_lower(loc) for loc in locations)):
        countries |= {"canada", "united states"}
    cities.discard("")
    return {"cities": cities, "provinces": provinces, "countries": countries}


def countries_in(location: str | None) -> set[str]:
    text = _lower(location)
    found = {country for country, pattern in COUNTRIES.items() if re.search(pattern, text)}
    if "north america" in text:
        found |= {"canada", "united states"}
    if any(re.search(rf",\s*{code}\b", text) or name in text for code, name in PROVINCES.items()):
        found.add("canada")
    return found


# Words in a location that aren't places: "Remote (Hybrid) - HQ" names no place at all.
NOT_PLACES = r"\b(remote|hybrid|flexible|work from home|wfh|home|office|offices|hq|headquarters|based|first|only|" \
             r"within|in|or|and|the|of|any|location|locations|multiple|various|can)\b"


def remote_open_to_you(location: str | None, area: dict) -> bool:
    """
    A remote job is open to you if its location names your country, province or
    city, or names no place at all ("Remote"). Naming only other places
    ("Remote, United States", "Remote - ME; NH", "Remote, Sweden") means it isn't.
    """
    if not area["countries"]:
        return True  # can't tell where you are, so don't guess
    text = _lower(location)
    if re.search(OPEN_TO_ALL, text) or any(city in text for city in area["cities"]):
        return True
    if countries_in(location) & area["countries"] or re.search(r"\bcan\b", text) and "canada" in area["countries"]:
        return True
    leftover = re.sub(r"[^a-z]+", " ", re.sub(NOT_PLACES, " ", text)).strip()
    return not leftover


def in_area(location: str | None, work_arrangement: str, area: dict) -> bool:
    if not (area["cities"] or area["provinces"] or area["countries"]):
        return True
    text = _lower(location)
    if location and _city(location) in area["cities"]:
        return True
    if any(city in text for city in area["cities"]):
        return True
    if any(re.search(rf"(,|\(|^)\s*{code}\b", text) or PROVINCES[code] in text for code in area["provinces"]):
        return True
    if work_arrangement == "remote" or "remote" in text:
        return remote_open_to_you(location, area)
    return False
