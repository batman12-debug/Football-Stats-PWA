"""Country flag URLs for World Cup 2026 teams."""

from __future__ import annotations

from app.services.data_sources.team_names import normalize_team_name

FLAG_CDN_BASE = "https://flagcdn.com/w80"

# ISO 3166-1 alpha-2 (or flagcdn regional codes for England/Scotland).
TEAM_FLAG_CODES: dict[str, str] = {
    "algeria": "dz",
    "argentina": "ar",
    "australia": "au",
    "austria": "at",
    "belgium": "be",
    "bosnia-herzegovina": "ba",
    "brazil": "br",
    "canada": "ca",
    "cape verde islands": "cv",
    "colombia": "co",
    "congo dr": "cd",
    "croatia": "hr",
    "curaçao": "cw",
    "czechia": "cz",
    "ecuador": "ec",
    "egypt": "eg",
    "england": "gb-eng",
    "france": "fr",
    "germany": "de",
    "ghana": "gh",
    "haiti": "ht",
    "iran": "ir",
    "iraq": "iq",
    "ivory coast": "ci",
    "japan": "jp",
    "jordan": "jo",
    "mexico": "mx",
    "morocco": "ma",
    "netherlands": "nl",
    "new zealand": "nz",
    "norway": "no",
    "panama": "pa",
    "paraguay": "py",
    "portugal": "pt",
    "qatar": "qa",
    "saudi arabia": "sa",
    "scotland": "gb-sct",
    "senegal": "sn",
    "south africa": "za",
    "south korea": "kr",
    "spain": "es",
    "sweden": "se",
    "switzerland": "ch",
    "tunisia": "tn",
    "turkey": "tr",
    "united states": "us",
    "uruguay": "uy",
    "uzbekistan": "uz",
}


def team_flag_code(name: str) -> str | None:
    return TEAM_FLAG_CODES.get(normalize_team_name(name))


def team_flag_url(name: str) -> str | None:
    code = team_flag_code(name)
    if not code:
        return None
    return f"{FLAG_CDN_BASE}/{code}.png"


def team_display_code(name: str) -> str | None:
    code = team_flag_code(name)
    if not code:
        return None
    if code.startswith("gb-"):
        return code.split("-", 1)[1].upper()
    return code.upper()
