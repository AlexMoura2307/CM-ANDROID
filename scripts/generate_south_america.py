from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
from hashlib import sha256
from io import BytesIO
from math import log10
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse
import argparse
import json
import random
import re
import shutil
import threading
import time
import unicodedata
import urllib.request

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit("Pillow is required: python -m pip install pillow") from exc

ROOT = Path("wfe-south-america")
QA_ROOT = Path("wfe-south-america-qa")
ASSETS_PLAYERS = ROOT / "assets" / "players" / "by-id"
ASSETS_CLUBS = ROOT / "assets" / "clubs" / "by-id"
TM_BASE = "https://transfermarkt-api.fly.dev"
SOFA_BASE = "https://www.sofascore.com/api/v1"
FOTMOB_SEARCH = "https://apigw.fotmob.com/searchapi/suggest"
FOTMOB_PLAYER_IMAGE = "https://images.fotmob.com/image_resources/playerimages/{id}.png"
ESPN_LEAGUE_CODES = {
    "AR": "arg.1",
    "BO": "bol.1",
    "BR": "bra.1",
    "CL": "chi.1",
    "CO": "col.1",
    "EC": "ecu.1",
    "PY": "par.1",
    "PE": "per.1",
    "UY": "uru.1",
    "VE": "ven.1",
}
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/140 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}

# O endpoint publico usado aqui informa limite de 2 requests a cada 3 segundos.
# Esta cadencia deixa a geracao previsivel e evita martelar a fonte.
_last_api_request_at = 0.0
_last_sofa_request_at = 0.0
_tm_lock = threading.Lock()
_last_fotmob_request_at = 0.0
_last_espn_request_at = 0.0
_sofa_lock = threading.Lock()
_fotmob_lock = threading.Lock()
_espn_lock = threading.Lock()
_espn_team_cache: dict[str, list[dict]] = {}
_affiliate_search_cache: dict[tuple[str, str], dict[str, dict | None]] = {}


@dataclass(frozen=True)
class CompetitionSpec:
    key: str
    country_code: str
    country_name: str
    display_name: str
    aliases: tuple[str, ...]
    priority: int
    legs: int
    min_clubs: int
    division: int = 1
    source_id: str | None = None


COMPETITIONS: tuple[CompetitionSpec, ...] = (
    CompetitionSpec(
        "arg-primera", "AR", "Argentina", "Liga Profesional Argentina",
        ("Liga Profesional", "Primera Division Argentina", "Primera División Argentina"),
        10, 2, 20, 1, "ARG1",
    ),
    CompetitionSpec(
        "bol-primera", "BO", "Bolivia", "Division Profesional Bolivia",
        ("Division Profesional", "División Profesional", "Primera Division Bolivia"),
        10, 2, 14, 1, "BO1A",
    ),
    CompetitionSpec(
        "bra-serie-a", "BR", "Brazil", "Campeonato Brasileiro Serie A",
        ("Campeonato Brasileiro Serie A", "Brasileirao Serie A", "Brasileirão Série A"),
        10, 2, 18, 1, "BRA1",
    ),
    CompetitionSpec(
        "bra-serie-b", "BR", "Brazil", "Campeonato Brasileiro Serie B",
        ("Campeonato Brasileiro Serie B", "Brasileirao Serie B", "Brasileirão Série B"),
        20, 2, 18, 2, "BRA2",
    ),
    CompetitionSpec(
        "bra-serie-c", "BR", "Brazil", "Campeonato Brasileiro Serie C",
        ("Campeonato Brasileiro Serie C", "Brasileirao Serie C", "Brasileirão Série C"),
        30, 1, 18, 3, "BRA3",
    ),
    CompetitionSpec(
        "chi-primera", "CL", "Chile", "Primera Division de Chile",
        ("Primera Division de Chile", "Primera División de Chile", "Primera Division Chile"),
        10, 2, 14, 1, "CLPD",
    ),
    CompetitionSpec(
        "col-primera-a", "CO", "Colombia", "Primera A Colombia",
        ("Primera A Colombia", "Liga Dimayor", "Categoria Primera A"),
        10, 2, 18, 1, "COLP",
    ),
    CompetitionSpec(
        "ecu-serie-a", "EC", "Ecuador", "LigaPro Serie A",
        ("LigaPro Serie A", "Serie A Ecuador", "Primera Etapa Ecuador"),
        10, 2, 14, 1, "EC1N",
    ),
    CompetitionSpec(
        "par-primera", "PY", "Paraguay", "Primera Division Paraguay",
        ("Primera Division Paraguay", "Primera División Paraguay", "Division Profesional Paraguay"),
        10, 2, 10, 1, "PR1A",
    ),
    CompetitionSpec(
        "per-liga-1", "PE", "Peru", "Liga 1 Peru",
        ("Liga 1 Peru", "Liga 1", "Primera Division Peru"),
        10, 2, 16, 1, "TDeA",
    ),
    CompetitionSpec(
        "uru-primera", "UY", "Uruguay", "Primera Division Uruguay",
        ("Primera Division Uruguay", "Primera División Uruguay", "Liga AUF Uruguaya"),
        10, 2, 14, 1, "URU1",
    ),
    CompetitionSpec(
        "ven-primera", "VE", "Venezuela", "Liga FUTVE",
        ("Liga FUTVE", "Primera Division Venezuela", "Primera División Venezuela"),
        10, 2, 12, 1, "VZ1A",
    ),
)

COUNTRY_ALIASES = {
    "argentina": {"argentina"},
    "bolivia": {"bolivia"},
    "brazil": {"brazil", "brasil"},
    "chile": {"chile"},
    "colombia": {"colombia"},
    "ecuador": {"ecuador"},
    "paraguay": {"paraguay"},
    "peru": {"peru", "perú"},
    "uruguay": {"uruguay"},
    "venezuela": {"venezuela"},
}

COUNTRY_NAME_TO_CODE = {
    # CONMEBOL
    "argentina": "AR", "bolivia": "BO", "brazil": "BR", "brasil": "BR",
    "chile": "CL", "colombia": "CO", "ecuador": "EC", "paraguay": "PY",
    "peru": "PE", "perú": "PE", "uruguay": "UY", "venezuela": "VE",
    # Americas
    "mexico": "MX", "méxico": "MX", "united states": "US", "usa": "US",
    "canada": "CA", "costa rica": "CR", "panama": "PA", "panamá": "PA",
    "honduras": "HN", "guatemala": "GT", "el salvador": "SV",
    "dominican republic": "DO", "jamaica": "JM", "haiti": "HT",
    # Europe
    "portugal": "PT", "spain": "ES", "españa": "ES", "france": "FR",
    "germany": "DE", "italy": "IT", "england": "ENG", "scotland": "SCO",
    "wales": "WAL", "northern ireland": "NIR", "netherlands": "NL",
    "belgium": "BE", "switzerland": "CH", "austria": "AT", "croatia": "HR",
    "serbia": "RS", "bosnia-herzegovina": "BA", "bosnia and herzegovina": "BA",
    "slovenia": "SI", "slovakia": "SK", "czech republic": "CZ", "czechia": "CZ",
    "poland": "PL", "romania": "RO", "bulgaria": "BG", "greece": "GR",
    "turkey": "TR", "ukraine": "UA", "russia": "RU", "denmark": "DK",
    "norway": "NO", "sweden": "SE", "finland": "FI", "iceland": "IS",
    "ireland": "IE", "albania": "AL", "montenegro": "ME", "north macedonia": "MK",
    # Africa
    "morocco": "MA", "algeria": "DZ", "tunisia": "TN", "egypt": "EG",
    "ghana": "GH", "nigeria": "NG", "senegal": "SN", "cameroon": "CM",
    "ivory coast": "CI", "côte d'ivoire": "CI", "south africa": "ZA",
    "angola": "AO", "cape verde": "CV", "guinea": "GN", "mali": "ML",
    # Asia/Oceania
    "japan": "JP", "south korea": "KR", "korea, south": "KR", "china": "CN",
    "australia": "AU", "new zealand": "NZ", "saudi arabia": "SA",
    "united arab emirates": "AE", "iran": "IR", "iraq": "IQ", "israel": "IL",
}

TM_POSITION_MAP = {
    "goalkeeper": "Goalkeeper",
    "centre back": "CenterBack",
    "center back": "CenterBack",
    "sweeper": "CenterBack",
    "left back": "LeftBack",
    "right back": "RightBack",
    "left wing back": "LeftWingBack",
    "right wing back": "RightWingBack",
    "defensive midfield": "DefensiveMidfielder",
    "central midfield": "CentralMidfielder",
    "attacking midfield": "AttackingMidfielder",
    "left midfield": "LeftMidfielder",
    "right midfield": "RightMidfielder",
    "left winger": "LeftWinger",
    "right winger": "RightWinger",
    "centre forward": "Striker",
    "center forward": "Striker",
    "second striker": "Striker",
    "striker": "Striker",
    "forward": "Striker",
}

COLOR_NAMES = {
    "black": "#111111", "white": "#ffffff", "red": "#d71920", "green": "#167c45",
    "blue": "#1857a4", "light blue": "#55a9e2", "sky blue": "#55a9e2",
    "yellow": "#f3d21b", "orange": "#e97819", "purple": "#6f42a3", "violet": "#6f42a3",
    "pink": "#d56a9d", "maroon": "#7a1538", "burgundy": "#7a1538",
    "navy": "#13294b", "grey": "#777777", "gray": "#777777", "gold": "#c9a227",
}

ATTRIBUTE_KEYS = (
    "pace", "stamina", "strength", "agility",
    "passing", "shooting", "tackling", "dribbling", "defending",
    "positioning", "vision", "decisions", "composure", "aggression",
    "teamwork", "leadership", "handling", "reflexes", "aerial",
)

# Pesos inspirados conceitualmente em um manager profundo: a nota de cada atributo
# depende da funcao/posicao. Nao copia banco proprietario de outro jogo.
POSITION_DELTAS = {
    "Goalkeeper": {
        "pace": -14, "stamina": -8, "strength": 3, "agility": 4,
        "passing": -4, "shooting": -28, "tackling": -18, "dribbling": -18, "defending": -8,
        "positioning": 7, "vision": -2, "decisions": 6, "composure": 6,
        "aggression": -2, "teamwork": 2, "leadership": 3,
        "handling": 12, "reflexes": 14, "aerial": 10,
    },
    "CenterBack": {
        "pace": -2, "stamina": 2, "strength": 8, "agility": -1,
        "passing": 0, "shooting": -12, "tackling": 10, "dribbling": -7, "defending": 11,
        "positioning": 10, "vision": -2, "decisions": 6, "composure": 4,
        "aggression": 6, "teamwork": 5, "leadership": 4,
        "handling": -28, "reflexes": -25, "aerial": 7,
    },
    "LeftBack": {
        "pace": 8, "stamina": 8, "strength": 1, "agility": 6,
        "passing": 4, "shooting": -7, "tackling": 6, "dribbling": 3, "defending": 6,
        "positioning": 5, "vision": 1, "decisions": 3, "composure": 1,
        "aggression": 3, "teamwork": 5, "leadership": 0,
        "handling": -30, "reflexes": -26, "aerial": -2,
    },
    "RightBack": {},
    "LeftWingBack": {},
    "RightWingBack": {},
    "DefensiveMidfielder": {
        "pace": 0, "stamina": 6, "strength": 5, "agility": 1,
        "passing": 6, "shooting": -5, "tackling": 8, "dribbling": 1, "defending": 7,
        "positioning": 8, "vision": 5, "decisions": 7, "composure": 5,
        "aggression": 5, "teamwork": 7, "leadership": 3,
        "handling": -30, "reflexes": -27, "aerial": 1,
    },
    "CentralMidfielder": {
        "pace": 1, "stamina": 6, "strength": 1, "agility": 3,
        "passing": 9, "shooting": 0, "tackling": 2, "dribbling": 5, "defending": 1,
        "positioning": 4, "vision": 9, "decisions": 8, "composure": 6,
        "aggression": 1, "teamwork": 7, "leadership": 2,
        "handling": -30, "reflexes": -27, "aerial": -3,
    },
    "AttackingMidfielder": {
        "pace": 4, "stamina": 2, "strength": -3, "agility": 7,
        "passing": 8, "shooting": 6, "tackling": -10, "dribbling": 10, "defending": -10,
        "positioning": 4, "vision": 10, "decisions": 6, "composure": 7,
        "aggression": -2, "teamwork": 3, "leadership": 0,
        "handling": -30, "reflexes": -27, "aerial": -5,
    },
    "LeftMidfielder": {},
    "RightMidfielder": {},
    "LeftWinger": {
        "pace": 10, "stamina": 4, "strength": -3, "agility": 10,
        "passing": 5, "shooting": 5, "tackling": -12, "dribbling": 11, "defending": -12,
        "positioning": 4, "vision": 5, "decisions": 4, "composure": 5,
        "aggression": -3, "teamwork": 2, "leadership": -2,
        "handling": -30, "reflexes": -27, "aerial": -7,
    },
    "RightWinger": {},
    "Striker": {
        "pace": 6, "stamina": 1, "strength": 5, "agility": 5,
        "passing": -1, "shooting": 12, "tackling": -16, "dribbling": 6, "defending": -16,
        "positioning": 10, "vision": 1, "decisions": 5, "composure": 10,
        "aggression": 2, "teamwork": 1, "leadership": 1,
        "handling": -30, "reflexes": -27, "aerial": 4,
    },
}
POSITION_DELTAS["RightBack"] = dict(POSITION_DELTAS["LeftBack"])
POSITION_DELTAS["LeftWingBack"] = dict(POSITION_DELTAS["LeftBack"], passing=5, defending=4, dribbling=5)
POSITION_DELTAS["RightWingBack"] = dict(POSITION_DELTAS["LeftWingBack"])
POSITION_DELTAS["LeftMidfielder"] = dict(POSITION_DELTAS["CentralMidfielder"], pace=5, dribbling=6, tackling=-1)
POSITION_DELTAS["RightMidfielder"] = dict(POSITION_DELTAS["LeftMidfielder"])
POSITION_DELTAS["RightWinger"] = dict(POSITION_DELTAS["LeftWinger"])


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join("".join(ch if ch.isalnum() else " " for ch in text.lower()).split())


def slug(value: str) -> str:
    return norm(value).replace(" ", "-") or "club"


def clamp(value: float, low: int = 1, high: int = 99) -> int:
    return max(low, min(high, int(round(value))))


def deterministic_rng(*parts: object) -> random.Random:
    digest = sha256("|".join(str(x) for x in parts).encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def api_json(path: str) -> dict:
    global _last_api_request_at

    url = path if path.startswith("http") else TM_BASE + path
    last_error = None

    # A mesma rotina e usada por tarefas paralelas de foto. Serializar aqui
    # evita bursts/races e preserva o limite da fonte.
    with _tm_lock:
        elapsed = time.monotonic() - _last_api_request_at
        if elapsed < 1.60:
            time.sleep(1.60 - elapsed)

        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers=HTTP_HEADERS)
                _last_api_request_at = time.monotonic()
                with urllib.request.urlopen(req, timeout=45) as response:
                    return json.loads(response.read().decode("utf-8"))
            except Exception as exc:
                last_error = exc
                time.sleep(3 + attempt * 3)
    raise RuntimeError(f"Transfermarkt API indisponivel para {url}: {last_error}")


def sofa_json(path: str, params: dict | None = None) -> dict:
    global _last_sofa_request_at

    url = path if path.startswith("http") else SOFA_BASE + path
    if params:
        url += ("&" if "?" in url else "?") + urlencode(params)

    headers = dict(HTTP_HEADERS)
    headers["Referer"] = "https://www.sofascore.com/"

    # Serialize SofaScore requests even when player images are processed in a
    # thread pool. This keeps the fallback polite and prevents burst failures.
    with _sofa_lock:
        wait = 0.35 - (time.monotonic() - _last_sofa_request_at)
        if wait > 0:
            time.sleep(wait)

        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers=headers)
                _last_sofa_request_at = time.monotonic()
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except Exception:
                time.sleep(1.5 + attempt * 2)
    return {}


def identity_norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(
        "".join(ch if ch.isalnum() else " " for ch in text.lower()).split()
    )


def sofa_date_of_birth(player: dict) -> str | None:
    direct = str(player.get("dateOfBirth") or "").strip()
    if len(direct) >= 10 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", direct[:10]):
        return direct[:10]

    timestamp = player.get("dateOfBirthTimestamp")
    try:
        if timestamp is not None:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).date().isoformat()
    except Exception:
        pass
    return None


def sofa_entity(entry: dict) -> dict:
    if not isinstance(entry, dict):
        return {}
    entity = entry.get("entity")
    if isinstance(entity, dict):
        return entity
    player = entry.get("player")
    if isinstance(player, dict):
        return player
    return entry


def fotmob_get(url: str) -> dict:
    global _last_fotmob_request_at

    headers = dict(HTTP_HEADERS)
    headers["Referer"] = "https://www.fotmob.com/"

    with _fotmob_lock:
        wait = 0.12 - (time.monotonic() - _last_fotmob_request_at)
        if wait > 0:
            time.sleep(wait)
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers=headers)
                _last_fotmob_request_at = time.monotonic()
                with urllib.request.urlopen(request, timeout=25) as response:
                    return json.loads(response.read().decode("utf-8"))
            except Exception:
                time.sleep(0.8 + attempt * 1.2)
    return {}


def fotmob_json(name: str) -> dict:
    query = urlencode({"term": name, "lang": "en"})
    return fotmob_get(FOTMOB_SEARCH + "?" + query)


def fotmob_player_data(fotmob_id: str, qa: dict) -> dict:
    qa["fotmobPlayerDataRequests"] = qa.get("fotmobPlayerDataRequests", 0) + 1
    payload = fotmob_get(
        "https://www.fotmob.com/api/data/playerData?"
        + urlencode({"id": fotmob_id})
    )
    if payload:
        qa["fotmobPlayerDataResponses"] = qa.get("fotmobPlayerDataResponses", 0) + 1
    return payload


def fotmob_birth_date(payload: dict) -> str | None:
    birth = payload.get("birthDate")
    if isinstance(birth, dict):
        raw = str(birth.get("utcTime") or "").strip()
    else:
        raw = str(birth or "").strip()
    if len(raw) >= 10 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw[:10]):
        return raw[:10]
    return None


def espn_json(url: str) -> dict:
    global _last_espn_request_at
    headers = dict(HTTP_HEADERS)
    headers["Referer"] = "https://www.espn.com/"

    with _espn_lock:
        wait = 0.08 - (time.monotonic() - _last_espn_request_at)
        if wait > 0:
            time.sleep(wait)
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers=headers)
                _last_espn_request_at = time.monotonic()
                with urllib.request.urlopen(request, timeout=25) as response:
                    return json.loads(response.read().decode("utf-8"))
            except Exception:
                time.sleep(0.7 + attempt)
    return {}


def espn_teams(country_code: str, qa: dict) -> list[dict]:
    if country_code in _espn_team_cache:
        return _espn_team_cache[country_code]
    league = ESPN_LEAGUE_CODES.get(country_code)
    if not league:
        return []
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams"
    payload = espn_json(url)
    entries = []
    try:
        entries = payload["sports"][0]["leagues"][0]["teams"]
    except (KeyError, IndexError, TypeError):
        entries = payload.get("teams", [])

    teams = []
    for entry in entries:
        team = entry.get("team") if isinstance(entry, dict) else None
        team = team or entry
        if isinstance(team, dict) and team.get("id"):
            teams.append(team)
    _espn_team_cache[country_code] = teams
    if teams:
        qa["espnLeagueTeamsLoaded"] = qa.get("espnLeagueTeamsLoaded", 0) + len(teams)
    return teams


def espn_roster_items(payload: dict) -> list[dict]:
    result = []
    for group in payload.get("athletes", []):
        if isinstance(group, dict) and isinstance(group.get("items"), list):
            result.extend(group["items"])
        elif isinstance(group, dict) and group.get("id"):
            result.append(group)
    return [
        item for item in result
        if isinstance(item, dict) and item.get("id")
    ]


def espn_birth_date(player: dict) -> str | None:
    raw = player.get("birthDate") or player.get("dateOfBirth")
    text = str(raw or "").strip()
    if len(text) >= 10 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", text[:10]):
        return text[:10]
    return None


def espn_player_name(player: dict) -> str:
    return str(
        player.get("displayName")
        or player.get("fullName")
        or player.get("name")
        or ""
    ).strip()


def espn_headshot_url(player: dict) -> str | None:
    headshot = player.get("headshot")
    if isinstance(headshot, dict):
        href = str(headshot.get("href") or "").strip()
        return href or None
    if isinstance(headshot, str) and headshot.strip():
        return headshot.strip()
    return None


def espn_club_roster(
    club_name: str,
    country_code: str,
    qa: dict,
) -> list[dict]:
    teams = espn_teams(country_code, qa)
    if not teams:
        return []

    target = identity_norm(club_name)
    candidates = []
    for team in teams:
        names = [
            team.get("displayName"),
            team.get("name"),
            team.get("shortDisplayName"),
            team.get("nickname"),
        ]
        scores = []
        for value in names:
            candidate = identity_norm(value)
            if not candidate:
                continue
            ratio = SequenceMatcher(None, target, candidate).ratio()
            target_tokens = set(target.split())
            candidate_tokens = set(candidate.split())
            overlap = len(target_tokens & candidate_tokens) / max(
                1, min(len(target_tokens), len(candidate_tokens))
            )
            contains = (
                target in candidate or candidate in target
                if min(len(target), len(candidate)) >= 4
                else False
            )
            scores.append(max(ratio, overlap, 0.96 if contains else 0.0))
        if scores:
            candidates.append((max(scores), team))

    if not candidates:
        return []
    score, team = max(candidates, key=lambda item: item[0])
    if score < 0.72:
        return []

    league = ESPN_LEAGUE_CODES[country_code]
    payload = espn_json(
        f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/{team['id']}/roster"
    )
    roster = espn_roster_items(payload)
    if roster:
        qa["espnClubMatches"] = qa.get("espnClubMatches", 0) + 1
        qa["espnRosterPlayers"] = qa.get("espnRosterPlayers", 0) + len(roster)
    return roster


def espn_photo_map(
    club_name: str,
    country_code: str,
    tm_players: list[dict],
    qa: dict,
) -> dict[str, str]:
    roster = espn_club_roster(club_name, country_code, qa)
    if not roster:
        return {}

    result = {}
    for tm_player in tm_players:
        target_name = identity_norm(tm_player.get("name"))
        if not target_name:
            continue
        target_dob = str(tm_player.get("dateOfBirth") or "")[:10]
        candidates = []

        for player in roster:
            photo = espn_headshot_url(player)
            if not photo:
                continue
            candidate_name = identity_norm(espn_player_name(player))
            if not candidate_name:
                continue
            ratio = SequenceMatcher(None, target_name, candidate_name).ratio()
            birth = espn_birth_date(player)

            if target_dob and birth:
                if target_dob != birth or ratio < 0.55:
                    continue
                score = 3.0 + ratio
            else:
                if target_name != candidate_name and ratio < 0.94:
                    continue
                score = ratio
            candidates.append((score, photo))

        if candidates:
            _, photo = max(candidates, key=lambda item: item[0])
            result[str(tm_player["id"])] = photo

    qa["espnPlayerMatches"] = qa.get("espnPlayerMatches", 0) + len(result)
    return result


def club_name_matches(source_club: str, candidate_club: str) -> bool:
    a = identity_norm(source_club)
    b = identity_norm(candidate_club)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    ratio = SequenceMatcher(None, a, b).ratio()
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    overlap = len(a_tokens & b_tokens) / max(1, min(len(a_tokens), len(b_tokens)))
    return ratio >= 0.62 or overlap >= 0.60


def fotmob_player_photo(
    tm_player: dict,
    club_name: str,
    qa: dict,
) -> str | None:
    name = str(tm_player.get("name") or "").strip()
    if not name:
        return None

    target_name = identity_norm(name)
    target_dob = str(tm_player.get("dateOfBirth") or "")[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", target_dob):
        target_dob = ""

    # Try the exact display name first, then an accent-free spelling and finally
    # the surname when necessary. All candidates still need identity validation.
    queries = [name]
    ascii_name = identity_norm(name)
    if ascii_name and identity_norm(ascii_name) != target_name:
        queries.append(ascii_name)
    words = [w for w in ascii_name.split() if len(w) >= 3]
    if len(words) >= 2:
        queries.append(" ".join(words[-2:]))
        queries.append(words[-1])

    candidate_by_id = {}
    for query_name in dict.fromkeys(queries):
        qa["fotmobSearchRequests"] = qa.get("fotmobSearchRequests", 0) + 1
        payload = fotmob_json(query_name)
        groups = payload.get("squadMemberSuggest", [])
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            for option in group.get("options", []) or []:
                if not isinstance(option, dict):
                    continue
                payload_data = option.get("payload") or {}
                if payload_data.get("isCoach") is True:
                    continue
                fotmob_id = str(payload_data.get("id") or "").strip()
                if not fotmob_id:
                    continue
                option_text = str(option.get("text") or group.get("text") or "")
                candidate_name = option_text.split("|", 1)[0].strip()
                candidate_norm = identity_norm(candidate_name)
                if not candidate_norm:
                    continue
                ratio = SequenceMatcher(None, target_name, candidate_norm).ratio()
                token_overlap = len(set(target_name.split()) & set(candidate_norm.split())) / max(
                    1, min(len(set(target_name.split())), len(set(candidate_norm.split())))
                )
                if ratio < 0.72 and token_overlap < 0.75:
                    continue
                candidate_by_id[fotmob_id] = {
                    "name": candidate_name,
                    "nameRatio": ratio,
                    "tokenOverlap": token_overlap,
                    "suggestTeam": str(payload_data.get("teamName") or "").strip(),
                }

        # Exact full-name results are enough; avoid extra broad searches.
        if any(
            identity_norm(item["name"]) == target_name
            for item in candidate_by_id.values()
        ):
            break

    if not candidate_by_id:
        return None

    verified = []
    for fotmob_id, candidate in candidate_by_id.items():
        candidate_name_norm = identity_norm(candidate["name"])
        name_ratio = candidate["nameRatio"]
        exact_name = candidate_name_norm == target_name

        pdata = fotmob_player_data(fotmob_id, qa)
        if not pdata:
            continue

        pdata_name = identity_norm(pdata.get("name") or candidate["name"])
        pdata_ratio = SequenceMatcher(None, target_name, pdata_name).ratio()
        birth = fotmob_birth_date(pdata)
        primary_team = pdata.get("primaryTeam") or {}
        primary_team_name = str(primary_team.get("teamName") or candidate["suggestTeam"])

        # Highest-confidence path: same date of birth + related name.
        if target_dob and birth:
            if target_dob != birth:
                continue
            if max(name_ratio, pdata_ratio) < 0.60:
                continue
            score = 5.0 + max(name_ratio, pdata_ratio)
            if club_name_matches(club_name, primary_team_name):
                score += 0.5
            verified.append((score, fotmob_id, "dob"))
            continue

        # If DOB is unavailable from either source, require exact/near-exact
        # name plus the same current club. This is intentionally conservative.
        if not club_name_matches(club_name, primary_team_name):
            continue
        if not exact_name and max(name_ratio, pdata_ratio) < 0.97:
            continue
        score = 2.0 + max(name_ratio, pdata_ratio)
        verified.append((score, fotmob_id, "club"))

    if not verified:
        return None

    _, fotmob_id, verification = max(verified, key=lambda item: item[0])
    qa["fotmobPlayerMatches"] = qa.get("fotmobPlayerMatches", 0) + 1
    key = "fotmobDobVerified" if verification == "dob" else "fotmobClubVerified"
    qa[key] = qa.get(key, 0) + 1
    return FOTMOB_PLAYER_IMAGE.format(id=fotmob_id)


def sofa_team_squad(club_name: str, country_code: str, qa: dict) -> list[dict]:
    payload = sofa_json("/search/teams/", {"q": club_name, "page": 0})
    candidates = []
    target = identity_norm(club_name)

    for entry in payload.get("results", []):
        team = sofa_entity(entry)
        if not team:
            continue
        sport = team.get("sport") or {}
        if sport and sport.get("id") not in (None, 1):
            continue

        name = identity_norm(team.get("name") or team.get("shortName"))
        if not name:
            continue

        country = team.get("country") or {}
        alpha2 = str(country.get("alpha2") or "").upper()
        if alpha2 and alpha2 != country_code:
            continue

        ratio = SequenceMatcher(None, target, name).ratio()
        target_tokens = set(target.split())
        name_tokens = set(name.split())
        overlap = len(target_tokens & name_tokens) / max(
            1, min(len(target_tokens), len(name_tokens))
        )
        score = max(ratio, overlap)
        if alpha2 == country_code:
            score += 0.08
        candidates.append((score, team))

    if not candidates:
        return []

    score, team = max(candidates, key=lambda item: item[0])
    if score < 0.82 or not team.get("id"):
        return []

    squad_payload = sofa_json(f"/team/{team['id']}/players")
    raw_entries = squad_payload.get("players", [])
    squad = [sofa_entity(entry) for entry in raw_entries]
    squad = [player for player in squad if player.get("id") and player.get("name")]
    if squad:
        qa["sofaTeamMatches"] = qa.get("sofaTeamMatches", 0) + 1
    return squad


def match_sofa_player(tm_player: dict, sofa_squad: list[dict]) -> dict | None:
    target_name = identity_norm(tm_player.get("name"))
    if not target_name:
        return None
    target_dob = str(tm_player.get("dateOfBirth") or "")[:10]
    target_number = str(tm_player.get("shirtNumber") or "").strip()

    scored = []
    for candidate in sofa_squad:
        candidate_name = identity_norm(candidate.get("name"))
        if not candidate_name:
            continue
        ratio = SequenceMatcher(None, target_name, candidate_name).ratio()
        candidate_dob = sofa_date_of_birth(candidate)
        candidate_number = str(
            candidate.get("jerseyNumber") or candidate.get("shirtNumber") or ""
        ).strip()

        if target_dob and candidate_dob:
            if target_dob != candidate_dob:
                continue
            # Same DOB is strong identity evidence; still require a related name.
            if ratio >= 0.55:
                scored.append((1.20 + ratio, candidate))
            continue

        # Without DOB, demand a very strong name match. Shirt number can only
        # strengthen a match; it never overrides a weak name.
        score = ratio
        if target_number and candidate_number and target_number == candidate_number:
            score += 0.04
        if ratio >= 0.94:
            scored.append((score, candidate))

    if not scored:
        return None
    return max(scored, key=lambda item: item[0])[1]


def sofa_player_search_photo(
    tm_player: dict,
    club_name: str,
    country_code: str,
    qa: dict,
) -> str | None:
    name = str(tm_player.get("name") or "").strip()
    if not name:
        return None

    qa["sofaPlayerSearchRequests"] = qa.get("sofaPlayerSearchRequests", 0) + 1
    payload = sofa_json("/search/players/" + quote(name.lower(), safe=""))
    candidates = payload.get("players", [])
    if not isinstance(candidates, list):
        return None

    target_name = identity_norm(name)
    target_dob = str(tm_player.get("dateOfBirth") or "")[:10]
    target_club = identity_norm(club_name)

    matches = []
    for entry in candidates:
        candidate = sofa_entity(entry)
        if not candidate or not candidate.get("id"):
            continue

        candidate_name = identity_norm(candidate.get("name"))
        if not candidate_name:
            continue
        name_ratio = SequenceMatcher(None, target_name, candidate_name).ratio()
        if name_ratio < 0.90:
            continue

        candidate_dob = sofa_date_of_birth(candidate)
        candidate_team = candidate.get("team") or {}
        candidate_team_name = identity_norm(
            candidate_team.get("name") or candidate_team.get("shortName")
        )
        team_ratio = (
            SequenceMatcher(None, target_club, candidate_team_name).ratio()
            if target_club and candidate_team_name
            else 0.0
        )

        # DOB match is the strongest identity check. Without DOB, require an
        # almost-exact name AND a reasonably matching club.
        if target_dob and candidate_dob:
            if target_dob != candidate_dob:
                continue
            score = 2.0 + name_ratio + team_ratio * 0.25
        else:
            if name_ratio < 0.97 or team_ratio < 0.68:
                continue
            score = name_ratio + team_ratio

        matches.append((score, candidate))

    if not matches:
        return None

    _, candidate = max(matches, key=lambda item: item[0])
    qa["sofaPlayerSearchMatches"] = qa.get("sofaPlayerSearchMatches", 0) + 1
    return f"https://img.sofascore.com/api/v1/player/{candidate['id']}/image"


def sofa_photo_map(
    club_name: str,
    country_code: str,
    tm_players: list[dict],
    qa: dict,
) -> dict[str, str]:
    # Secondary source is used only to recover missing/unreachable real photos.
    # Identity is validated within the same club by DOB+name or an extremely
    # strong name match. The downloaded file is still stored under the TM ID.
    squad = sofa_team_squad(club_name, country_code, qa)
    if not squad:
        return {}

    result = {}
    for tm_player in tm_players:
        candidate = match_sofa_player(tm_player, squad)
        if not candidate:
            continue
        result[str(tm_player["id"])] = (
            f"https://img.sofascore.com/api/v1/player/{candidate['id']}/image"
        )
    qa["sofaPlayerMatches"] = qa.get("sofaPlayerMatches", 0) + len(result)
    return result


def image_bytes(url: str) -> bytes | None:
    if not url:
        return None
    candidates = [url]
    if "/big/" in url:
        candidates.insert(0, url.replace("/big/", "/medium/"))
    headers = dict(HTTP_HEADERS)
    headers["Accept"] = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
    for candidate in candidates:
        try:
            req = urllib.request.Request(candidate, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as response:
                data = response.read()
                if len(data) >= 512:
                    return data
        except Exception:
            continue
    return None


def download_asset(
    stable_id: str,
    url: str | None,
    folder: Path,
    *,
    logo: bool = False,
) -> str | None:
    if not url:
        return None
    data = image_bytes(url)
    if not data:
        return None

    dest = folder / f"{stable_id}.webp"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(BytesIO(data)) as source:
            source.thumbnail((192, 192), Image.Resampling.LANCZOS)
            if logo:
                image = source.convert("RGBA")
                image.save(dest, "WEBP", lossless=True, method=6)
            else:
                image = source.convert("RGB")
                image.save(dest, "WEBP", quality=78, method=6)
    except Exception:
        return None

    if not dest.exists() or dest.stat().st_size < 300:
        return None
    return dest.relative_to(ROOT).as_posix()

def country_code(name: str | None, fallback: str) -> str:
    if not name:
        return fallback
    return COUNTRY_NAME_TO_CODE.get(norm(name), fallback)


def tm_position(value: str | None) -> str:
    key = norm(str(value or "").replace("-", " "))
    if key in TM_POSITION_MAP:
        return TM_POSITION_MAP[key]
    if "goalkeeper" in key:
        return "Goalkeeper"
    if "back" in key and "left" in key:
        return "LeftBack"
    if "back" in key and "right" in key:
        return "RightBack"
    if "back" in key or "defender" in key:
        return "CenterBack"
    if "defensive" in key and "midfield" in key:
        return "DefensiveMidfielder"
    if "attacking" in key and "midfield" in key:
        return "AttackingMidfielder"
    if "midfield" in key:
        return "CentralMidfielder"
    if "winger" in key and "left" in key:
        return "LeftWinger"
    if "winger" in key and "right" in key:
        return "RightWinger"
    if "forward" in key or "striker" in key:
        return "Striker"
    return "CentralMidfielder"


def foot(value: str | None) -> str | None:
    key = norm(value)
    if not key:
        return None
    if "left" in key:
        return "Left"
    if "both" in key or "ambidextr" in key:
        return "Both"
    return "Right"


def color_hex(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        return text.lower()
    key = norm(text)
    for name, hex_value in COLOR_NAMES.items():
        if name in key:
            return hex_value
    return fallback


def team_colors(profile: dict, stable_id: str) -> tuple[str, str]:
    values = profile.get("colors") or []
    primary = color_hex(values[0] if len(values) > 0 else "", "")
    secondary = color_hex(values[1] if len(values) > 1 else "", "")
    if primary and secondary and primary != secondary:
        return primary, secondary

    rng = deterministic_rng(stable_id, "colors")
    hue = rng.randrange(0, 360)
    # Deterministic fallback. These are valid hex colors and only used when the source has none.
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(hue / 360.0, 0.72, 0.72)
    primary = primary or f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    secondary = secondary or "#ffffff"
    return primary, secondary


def estimate_overall(market_value: int | None, age: int | None, club_value: int | None) -> int:
    value = max(50_000, int(market_value or 50_000))
    # 50k ~= 52, 500k ~= 60, 5m ~= 68, 50m ~= 76, 150m ~= 80.
    rating = 52 + 8.0 * log10(value / 50_000)
    if club_value:
        club_bonus = max(-2.0, min(4.0, (log10(max(club_value, 1_000_000)) - 7.0) * 1.7))
        rating += club_bonus
    if age is not None and age <= 18:
        rating -= 2
    return clamp(rating, 45, 88)


def fm_style_attributes(
    player_id: str,
    position: str,
    overall: int,
    age: int | None,
    height_cm: int | None,
) -> dict:
    deltas = POSITION_DELTAS.get(position, POSITION_DELTAS["CentralMidfielder"])
    rng = deterministic_rng(player_id, position, overall)
    attrs = {}
    for key in ATTRIBUTE_KEYS:
        jitter = rng.randint(-5, 5)
        attrs[key] = clamp(overall + deltas.get(key, 0) + jitter, 15, 95)

    # Ajustes observaveis/reais que a fonte fornece.
    if height_cm:
        attrs["strength"] = clamp(attrs["strength"] + (height_cm - 180) * 0.22, 15, 95)
        attrs["aerial"] = clamp(attrs["aerial"] + (height_cm - 180) * 0.35, 15, 95)
        attrs["agility"] = clamp(attrs["agility"] - max(0, height_cm - 190) * 0.18, 15, 95)

    if age is not None:
        if age <= 20:
            attrs["pace"] = clamp(attrs["pace"] + 2, 15, 95)
            attrs["agility"] = clamp(attrs["agility"] + 2, 15, 95)
            attrs["decisions"] = clamp(attrs["decisions"] - 2, 15, 95)
            attrs["leadership"] = clamp(attrs["leadership"] - 4, 15, 95)
        elif age >= 32:
            attrs["pace"] = clamp(attrs["pace"] - min(8, age - 31), 15, 95)
            attrs["stamina"] = clamp(attrs["stamina"] - min(6, max(0, age - 33)), 15, 95)
            attrs["decisions"] = clamp(attrs["decisions"] + 2, 15, 95)
            attrs["composure"] = clamp(attrs["composure"] + 2, 15, 95)
            attrs["leadership"] = clamp(attrs["leadership"] + 3, 15, 95)

    # Jogadores de linha nao devem receber habilidade de goleiro alta por acaso.
    if position != "Goalkeeper":
        attrs["handling"] = min(attrs["handling"], 25)
        attrs["reflexes"] = min(attrs["reflexes"], 30)
    else:
        attrs["handling"] = max(attrs["handling"], 55)
        attrs["reflexes"] = max(attrs["reflexes"], 55)
        attrs["aerial"] = max(attrs["aerial"], 50)

    return attrs


def source_country_ids() -> dict[str, int]:
    payload = api_json("/countries/")
    wanted = {
        "AR": {"argentina"},
        "BO": {"bolivia"},
        "BR": {"brazil", "brasil"},
        "CL": {"chile"},
        "CO": {"colombia"},
        "EC": {"ecuador"},
        "PY": {"paraguay"},
        "PE": {"peru"},
        "UY": {"uruguay"},
        "VE": {"venezuela"},
    }
    result = {}
    for country in payload.get("countries", []):
        name = norm(country.get("name"))
        for code, aliases in wanted.items():
            if name in aliases and country.get("id") is not None:
                result[code] = int(country["id"])
    missing = sorted(set(wanted) - set(result))
    if missing:
        raise RuntimeError("Paises sem ID na fonte: " + ", ".join(missing))
    return result


def all_country_clubs(country_code: str, country_ids: dict[str, int]) -> list[dict]:
    country_id = country_ids[country_code]
    payload = api_json(f"/clubs/?country_id={country_id}")
    return [
        {"id": str(item["id"]), "name": item.get("name") or f"Club {item['id']}"}
        for item in payload.get("clubs", [])
        if item.get("id")
    ]


def _country_matches_source(candidate_country: str | None, country_name: str) -> bool:
    value = norm(candidate_country)
    wanted = COUNTRY_ALIASES.get(norm(country_name), {norm(country_name)})
    return not value or value in wanted


def looks_like_affiliate_club_name(name: str) -> bool:
    text = identity_norm(name)
    if not text:
        return False
    patterns = (
        r"\b(?:u|sub|under)\s?(17|18|19|20|21|23)\b$",
        r"\bjuvenil(es)?\b$",
        r"\byouth\b$",
        r"\bacademy\b$",
        r"\breserve(s)?\b$",
        r"\breserva(s)?\b$",
        r"\bsecond\s+team\b$",
        r"\s+b$",
        r"\s+ii$",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _affiliate_suffix(parent_name: str, candidate_name: str) -> str | None:
    parent = identity_norm(parent_name)
    candidate = identity_norm(candidate_name)
    if not parent or not candidate or parent == candidate:
        return None

    if candidate.startswith(parent + " "):
        return candidate[len(parent):].strip()

    parent_tokens = parent.split()
    candidate_tokens = candidate.split()
    common = len(set(parent_tokens) & set(candidate_tokens))
    overlap = common / max(1, len(set(parent_tokens)))
    if overlap < 0.80:
        return None

    remaining = list(candidate_tokens)
    for token in parent_tokens:
        if token in remaining:
            remaining.remove(token)
    return " ".join(remaining).strip() or None


def _affiliate_kind(parent_name: str, candidate: dict) -> str | None:
    candidate_name = str(candidate.get("name") or "")
    suffix = _affiliate_suffix(parent_name, candidate_name)
    if not suffix:
        return None

    url_text = identity_norm(candidate.get("url") or "")
    suffix_text = identity_norm(suffix)
    combined = f"{suffix_text} {url_text}"

    youth_patterns = (
        r"\bu\s?(17|18|19|20|21)\b",
        r"\bsub\s?(17|18|19|20|21)\b",
        r"\bunder\s?(17|18|19|20|21)\b",
        r"\bjuvenil\b",
        r"\byouth\b",
        r"\bacademy\b",
    )
    if any(re.search(pattern, combined) for pattern in youth_patterns):
        return "youth"

    reserve_patterns = (
        r"^b$",
        r"^ii$",
        r"^2$",
        r"\breserve(s)?\b",
        r"\breserva(s)?\b",
        r"\bsegunda\b",
        r"\bsecond\s+team\b",
    )
    if any(re.search(pattern, suffix_text) for pattern in reserve_patterns):
        return "reserve"

    return None


def _youth_priority(candidate: dict) -> tuple[int, int]:
    text = identity_norm(
        f"{candidate.get('name') or ''} {candidate.get('url') or ''}"
    )
    for age in (21, 20, 19, 18, 17):
        if re.search(rf"\b(?:u|sub|under)\s?{age}\b", text):
            # Prefer U20, then U19, then younger. U21 comes last because CM base
            # never accepts a player older than 20.
            rank = {20: 100, 19: 90, 18: 80, 17: 70, 21: 60}[age]
            return rank, int(candidate.get("squad") or 0)
    if "juvenil" in text or "youth" in text or "academy" in text:
        return 50, int(candidate.get("squad") or 0)
    return 0, int(candidate.get("squad") or 0)


def discover_affiliate_clubs(
    parent_club_id: str,
    parent_name: str,
    country_name: str,
    qa: dict,
    name_variants: list[str] | None = None,
) -> dict[str, dict | None]:
    variants = []
    for value in [parent_name, *(name_variants or [])]:
        text = str(value or "").strip()
        if text and identity_norm(text) not in {
            identity_norm(existing) for existing in variants
        }:
            variants.append(text)

    cache_key = (
        str(parent_club_id),
        "|".join(identity_norm(value) for value in variants),
    )
    if cache_key in _affiliate_search_cache:
        return _affiliate_search_cache[cache_key]

    reserves = []
    youths = []
    seen_ids = set()

    for query_name in variants[:4]:
        try:
            first = api_json(
                "/clubs/search/"
                + quote(query_name, safe="")
                + "?page_number=1"
            )
        except Exception:
            continue

        pages = [first]
        # Affiliate teams often rank just outside the first 10 results. Only
        # inspect page 2 when necessary to keep the batch bounded.
        if (
            int(first.get("lastPageNumber") or 1) > 1
            and (not reserves or not youths)
        ):
            try:
                pages.append(
                    api_json(
                        "/clubs/search/"
                        + quote(query_name, safe="")
                        + "?page_number=2"
                    )
                )
            except Exception:
                pass

        for payload in pages:
            for candidate in payload.get("results", []):
                if not isinstance(candidate, dict) or not candidate.get("id"):
                    continue
                candidate_id = str(candidate["id"])
                if candidate_id == str(parent_club_id) or candidate_id in seen_ids:
                    continue
                if not _country_matches_source(candidate.get("country"), country_name):
                    continue

                kind = None
                for base_name in variants:
                    kind = _affiliate_kind(base_name, candidate)
                    if kind:
                        break
                if not kind:
                    continue

                seen_ids.add(candidate_id)
                if kind == "reserve":
                    reserves.append(candidate)
                elif kind == "youth":
                    youths.append(candidate)

        if reserves and youths:
            break

    reserve = max(
        reserves,
        key=lambda item: int(item.get("squad") or 0),
        default=None,
    )
    youth = max(youths, key=_youth_priority, default=None)
    result = {"reserve": reserve, "youth": youth}
    _affiliate_search_cache[cache_key] = result

    if reserve:
        qa["reserveAffiliateClubs"] = qa.get("reserveAffiliateClubs", 0) + 1
    if youth:
        qa["youthAffiliateClubs"] = qa.get("youthAffiliateClubs", 0) + 1
    return result


def raw_player_age(raw: dict) -> int | None:
    age = raw.get("age")
    try:
        if age is not None:
            return int(age)
    except Exception:
        pass

    dob = str(raw.get("dateOfBirth") or "")[:10]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", dob):
        try:
            born = datetime.strptime(dob, "%Y-%m-%d").date()
            anchor = date(2026, 1, 1)
            return anchor.year - born.year - (
                (anchor.month, anchor.day) < (born.month, born.day)
            )
        except Exception:
            return None
    return None


def competition_parent_query(name: str) -> str:
    text = str(name or "").strip()
    patterns = (
        r"\s+(?:u|sub|under)[ -]?(?:17|18|19|20|21|23)\s*$",
        r"\s+(?:juvenil(?:es)?|youth|academy|reserve(?:s)?|reserva(?:s)?)\s*$",
        r"\s+(?:b|ii)\s*$",
    )
    previous = None
    while previous != text:
        previous = text
        for pattern in patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
    return text


def repair_competition_clubs(
    clubs: list[dict],
    spec: CompetitionSpec,
    qa: dict,
) -> list[dict]:
    repaired = []
    seen = set()

    for club in clubs:
        club_id = str(club.get("id") or "").strip()
        name = str(club.get("name") or "").strip()
        if not club_id:
            continue

        candidate = club
        if looks_like_affiliate_club_name(name):
            base_name = competition_parent_query(name)
            try:
                payload = api_json(
                    "/clubs/search/"
                    + quote(base_name, safe="")
                    + "?page_number=1"
                )
            except Exception:
                payload = {}

            best = None
            best_score = 0.0
            target = identity_norm(base_name)
            for item in payload.get("results", []):
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                if looks_like_affiliate_club_name(item.get("name") or ""):
                    continue
                if not _country_matches_source(item.get("country"), spec.country_name):
                    continue
                candidate_name = identity_norm(item.get("name") or "")
                if not candidate_name:
                    continue
                ratio = SequenceMatcher(None, target, candidate_name).ratio()
                target_tokens = set(target.split())
                candidate_tokens = set(candidate_name.split())
                overlap = len(target_tokens & candidate_tokens) / max(
                    1, min(len(target_tokens), len(candidate_tokens))
                )
                score = max(ratio, overlap)
                if score > best_score:
                    best_score = score
                    best = item

            if best and best_score >= 0.68:
                qa["competitionAffiliateCorrections"].append({
                    "competition": spec.key,
                    "affiliateId": club_id,
                    "affiliateName": name,
                    "parentId": str(best["id"]),
                    "parentName": best.get("name"),
                    "score": round(best_score, 4),
                })
                candidate = best
                club_id = str(best["id"])
            else:
                qa["competitionAffiliateUnresolved"].append({
                    "competition": spec.key,
                    "affiliateId": club_id,
                    "affiliateName": name,
                })
                continue

        if club_id in seen:
            continue
        seen.add(club_id)
        repaired.append(candidate)

    return repaired


def resolve_competition(spec: CompetitionSpec) -> dict:
    # IDs oficiais do Transfermarkt sao preferidos: evitam confundir Apertura,
    # Clausura, copa da liga ou nomes antigos da mesma competicao.
    if spec.source_id:
        print(f"[competition] {spec.key}: {spec.display_name} [{spec.source_id}]")
        return {"id": spec.source_id, "name": spec.display_name}

    wanted_countries = COUNTRY_ALIASES.get(norm(spec.country_name), {norm(spec.country_name)})
    best = None
    best_score = -1.0

    for alias in spec.aliases:
        payload = api_json("/competitions/search/" + quote(alias, safe=""))
        for candidate in payload.get("results", []):
            cid = candidate.get("id")
            if not cid:
                continue
            candidate_name = norm(candidate.get("name"))
            candidate_country = norm(candidate.get("country"))
            if candidate_country and candidate_country not in wanted_countries:
                continue

            name_score = 0.0
            alias_norm = norm(alias)
            if candidate_name == alias_norm:
                name_score = 1.0
            elif alias_norm in candidate_name or candidate_name in alias_norm:
                name_score = 0.88
            else:
                # Token overlap is robust to "Liga 1 - Apertura" style variants.
                a = set(alias_norm.split())
                b = set(candidate_name.split())
                name_score = len(a & b) / max(1, len(a | b))

            country_bonus = 0.25 if candidate_country in wanted_countries else 0.0
            score = name_score + country_bonus
            if score > best_score:
                best = candidate
                best_score = score

        if best_score >= 1.15:
            break

    if best is None or best_score < 0.70:
        raise RuntimeError(
            f"Competicao nao localizada com seguranca: {spec.key} ({spec.country_name})"
        )
    print(f"[competition] {spec.key}: {best.get('name')} [{best.get('id')}]")
    return best


def city_from_profile(profile: dict, country_name: str) -> str:
    for key in ("addressLine2", "addressLine3", "addressLine1"):
        value = str(profile.get(key) or "").strip()
        if value:
            # Retira CEP/codigo postal inicial quando houver.
            value = re.sub(r"^[A-Z0-9 -]{2,12}\s+", "", value).strip(" ,")
            if value:
                return value[:80]
    stadium = profile.get("stadium") or {}
    value = str(stadium.get("addressLine2") or "").strip()
    if value:
        return value[:80]
    return country_name


def short_name(profile: dict, club_name: str) -> str:
    for key in ("abbreviation", "clubCode", "shortName"):
        value = str(profile.get(key) or "").strip()
        if value:
            return value[:5].upper()
    words = [w for w in re.split(r"\s+", club_name) if w]
    letters = "".join(w[0] for w in words[:4]).upper()
    return (letters or club_name[:3]).upper()[:5]


def reputation_and_finance(club_value: int | None) -> tuple[list[int], list[int]]:
    value = max(500_000, int(club_value or 500_000))
    rep_mid = clamp(300 + 95 * log10(value / 500_000), 260, 920)
    rep = [max(0, rep_mid - 20), min(1000, rep_mid + 20)]
    low = max(250_000, int(value * 0.08))
    high = max(low + 250_000, int(value * 0.25))
    return rep, [low, high]


def build_team(profile: dict, spec: CompetitionSpec, logo_path: str | None) -> dict:
    club_id = str(profile["id"])
    stable_id = f"tm-club-{club_id}"
    name = profile.get("officialName") or profile.get("name") or f"Club {club_id}"
    primary, secondary = team_colors(profile, stable_id)
    rep, finance = reputation_and_finance(profile.get("currentMarketValue"))
    team = {
        "id": stable_id,
        "name": name,
        "shortName": short_name(profile, name),
        "city": city_from_profile(profile, spec.country_name),
        "country": spec.country_code,
        "colors": {"primary": primary, "secondary": secondary},
        "playStyle": "Balanced",
        "stadiumName": profile.get("stadiumName") or "",
        "reputationRange": rep,
        "financeRange": finance,
    }
    if logo_path:
        team["logo"] = logo_path
    return team


def enrich_missing_player_photo(raw: dict, qa: dict) -> dict:
    """Fetch the player's own TM profile when the roster row has no photo.

    The lookup is always by the same Transfermarkt player ID, so a recovered
    photo cannot drift to a namesake. Profile data also fills missing real
    biographical fields when available.
    """
    if raw.get("imageUrl"):
        return raw

    qa["profileFallbackRequests"] = qa.get("profileFallbackRequests", 0) + 1
    player_id = str(raw.get("id") or "").strip()
    if not player_id:
        return raw

    try:
        profile = api_json(f"/players/{player_id}/profile")
    except Exception:
        return raw

    enriched = dict(raw)
    image_url = profile.get("imageUrl") or profile.get("image_url")
    if image_url:
        enriched["imageUrl"] = str(image_url)
        qa["profileFallbackPhotos"] = qa.get("profileFallbackPhotos", 0) + 1

    mapping = {
        "dateOfBirth": ("dateOfBirth", "date_of_birth"),
        "age": ("age",),
        "height": ("height",),
        "foot": ("foot",),
        "marketValue": ("marketValue", "market_value"),
    }
    for target, source_keys in mapping.items():
        if enriched.get(target) not in (None, "", []):
            continue
        for source_key in source_keys:
            value = profile.get(source_key)
            if value not in (None, "", []):
                enriched[target] = value
                break

    citizenship = profile.get("citizenship") or profile.get("nationality")
    if not enriched.get("nationality") and citizenship:
        enriched["nationality"] = citizenship if isinstance(citizenship, list) else [citizenship]

    position = profile.get("position")
    if isinstance(position, dict):
        main_position = position.get("main")
        if main_position:
            enriched["position"] = main_position
    elif position and not enriched.get("position"):
        enriched["position"] = position

    club = profile.get("club")
    if isinstance(club, dict) and not enriched.get("contract"):
        contract = club.get("contractExpires") or club.get("contract_expires")
        if contract:
            enriched["contract"] = contract

    return enriched


def build_player(
    raw: dict,
    team_id: str,
    home_country: str,
    club_value: int | None,
    photo_path: str | None,
) -> dict:
    tm_id = str(raw["id"])
    stable_id = f"tm-player-{tm_id}"
    display_name = str(raw.get("name") or f"Jogador {tm_id}").strip()
    bits = display_name.split()
    first = bits[0] if bits else display_name
    last = " ".join(bits[1:]) if len(bits) > 1 else first
    pos = tm_position(raw.get("position"))

    dob = str(raw.get("dateOfBirth") or "")[:10]
    age = raw.get("age")
    if age is None and dob:
        try:
            born = datetime.strptime(dob, "%Y-%m-%d").date()
            today = date(2026, 1, 1)
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        except Exception:
            age = None
    try:
        age = int(age) if age is not None else None
    except Exception:
        age = None

    value = raw.get("marketValue")
    value = int(value) if isinstance(value, (int, float)) and value >= 0 else None
    height = raw.get("height")
    try:
        height = int(height) if height else None
    except Exception:
        height = None

    overall = estimate_overall(value, age, club_value)
    attrs = fm_style_attributes(stable_id, pos, overall, age, height)

    nationalities = raw.get("nationality") or []
    nationality = country_code(nationalities[0] if nationalities else None, home_country)

    item = {
        "id": stable_id,
        "name": display_name,
        "firstName": first,
        "lastName": last,
        "club": team_id,
        "nationality": nationality,
        "position": pos,
        "attributes": attrs,
        "youth": False,
    }

    if dob:
        item["dateOfBirth"] = dob
    elif age is not None:
        item["age"] = age

    preferred_foot = foot(raw.get("foot"))
    if preferred_foot:
        item["footedness"] = preferred_foot
    if value is not None:
        item["value"] = value

    contract_end = str(raw.get("contract") or "")[:10]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", contract_end):
        item["contractEnd"] = contract_end

    if photo_path:
        item["photo"] = photo_path

    return item


def prepare_root() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    if QA_ROOT.exists():
        shutil.rmtree(QA_ROOT)
    (ROOT / "teams").mkdir(parents=True)
    (ROOT / "players").mkdir(parents=True)
    (ROOT / "competitions").mkdir(parents=True)
    ASSETS_PLAYERS.mkdir(parents=True)
    ASSETS_CLUBS.mkdir(parents=True)
    QA_ROOT.mkdir(parents=True)


def generate(country_filter: set[str] | None = None) -> dict:
    prepare_root()

    specs = [
        spec for spec in COMPETITIONS
        if not country_filter or spec.country_code in country_filter
    ]
    if not specs:
        raise RuntimeError("Nenhum pais selecionado para geracao.")

    teams_by_id: dict[str, dict] = {}
    players_by_id: dict[str, dict] = {}
    competition_defs: list[dict] = []
    country_ids = source_country_ids()
    expanded_countries: set[str] = set()
    processed_source_clubs: set[str] = set()
    qa = {
        "countries": {},
        "competitions": {},
        "clubsTotal": 0,
        "playersTotal": 0,
        "playersWithPhotos": 0,
        "clubsWithLogos": 0,
        "positionCounts": {},
        "rosterWarnings": [],
        "squadSegments": {},
        "segmentStats": {
            "seniorMain": {"players": 0, "withPhotos": 0},
            "topDivisionMain": {"players": 0, "withPhotos": 0},
            "reserveAffiliate": {"players": 0, "withPhotos": 0},
            "youthBase": {"players": 0, "withPhotos": 0},
        },
        "playableSquadFailures": [],
        "reserveAffiliateClubs": 0,
        "youthAffiliateClubs": 0,
        "reservePlayersImported": 0,
        "youthPlayersImported": 0,
        "youthPlayersSkippedOver20": 0,
        "youthPlayersSkippedUnknownAge": 0,
        "clubsWithoutYouthSource": [],
        "affiliateCatalogEntriesExcluded": [],
        "competitionAffiliateCorrections": [],
        "competitionAffiliateUnresolved": [],
        "youthBackfillRequired": [],
        "countryCatalogCounts": {},
        "profileFallbackRequests": 0,
        "profileFallbackPhotos": 0,
        "sofaTeamMatches": 0,
        "sofaPlayerMatches": 0,
        "sofaFallbackPhotos": 0,
        "sofaPlayerSearchRequests": 0,
        "sofaPlayerSearchMatches": 0,
        "fotmobSearchRequests": 0,
        "fotmobPlayerMatches": 0,
        "fotmobPlayerDataRequests": 0,
        "fotmobPlayerDataResponses": 0,
        "fotmobDobVerified": 0,
        "fotmobClubVerified": 0,
        "fotmobFallbackPhotos": 0,
        "espnLeagueTeamsLoaded": 0,
        "espnClubMatches": 0,
        "espnRosterPlayers": 0,
        "espnPlayerMatches": 0,
        "espnFallbackPhotos": 0,
        "source": "Transfermarkt public JSON API + identity-validated ESPN/FotMob photo fallback",
        "attributeModel": "FM-style conceptual role weights over real market/biographical data; no proprietary FM database copied",
    }

    for spec in specs:
        print(f"\n=== LOTE PAIS {spec.country_code} / {spec.display_name} ===")
        remote_comp = resolve_competition(spec)
        clubs_payload = api_json(f"/competitions/{remote_comp['id']}/clubs")
        competition_clubs = [
            club for club in clubs_payload.get("clubs", [])
            if club.get("id")
        ]
        competition_clubs = repair_competition_clubs(
            competition_clubs,
            spec,
            qa,
        )
        if len(competition_clubs) < spec.min_clubs:
            raise RuntimeError(
                f"{spec.key}: apenas {len(competition_clubs)} clubes; minimo esperado {spec.min_clubs}"
            )

        # No primeiro lote de cada pais, amplia a carga para TODOS os clubes
        # que a fonte publica consegue listar para aquele pais. As competicoes
        # continuam com seus participantes reais; o catalogo ampliado serve ao
        # Mundo/Clubes e aos elencos dos clubes fora da primeira divisao.
        raw_clubs = list(competition_clubs)
        if spec.country_code not in expanded_countries:
            country_clubs = all_country_clubs(spec.country_code, country_ids)
            primary_country_clubs = []
            competition_ids = {
                str(club["id"]) for club in competition_clubs if club.get("id")
            }
            for club in country_clubs:
                club_id = str(club.get("id") or "")
                if (
                    club_id not in competition_ids
                    and looks_like_affiliate_club_name(club.get("name") or "")
                ):
                    qa["affiliateCatalogEntriesExcluded"].append({
                        "country": spec.country_code,
                        "id": club_id,
                        "name": club.get("name"),
                    })
                    continue
                primary_country_clubs.append(club)

            qa["countryCatalogCounts"][spec.country_code] = len(primary_country_clubs)
            by_id = {str(club["id"]): club for club in raw_clubs}
            for club in primary_country_clubs:
                by_id.setdefault(str(club["id"]), club)
            raw_clubs = list(by_id.values())
            expanded_countries.add(spec.country_code)

        participant_ids: list[str] = [
            f"tm-club-{club['id']}" for club in competition_clubs
        ]
        competition_source_ids = {
            str(club["id"]) for club in competition_clubs if club.get("id")
        }
        comp_player_count = 0
        comp_photo_count = 0
        comp_logo_count = 0

        for index, raw_club in enumerate(raw_clubs, start=1):
            club_id = str(raw_club.get("id") or "").strip()
            if not club_id:
                continue
            if club_id in processed_source_clubs:
                continue
            processed_source_clubs.add(club_id)
            print(f"[{spec.key}] clube {index}/{len(raw_clubs)}: {raw_club.get('name')} ({club_id})")

            profile = api_json(f"/clubs/{club_id}/profile")
            if not profile.get("id"):
                profile["id"] = club_id
            roster = api_json(f"/clubs/{club_id}/players")

            team_stable_id = f"tm-club-{club_id}"
            logo_path = download_asset(team_stable_id, profile.get("image"), ASSETS_CLUBS, logo=True)
            if logo_path:
                comp_logo_count += 1

            team = build_team(profile, spec, logo_path)
            # O mesmo clube pode aparecer em mais de uma competicao; fica cadastrado uma vez.
            teams_by_id[team["id"]] = team
            club_value = profile.get("currentMarketValue")

            raw_players = [
                p for p in roster.get("players", [])
                if isinstance(p, dict) and p.get("id")
            ]

            # Elenco completo CM:
            # - principal/reserva: todo o elenco senior do clube principal;
            # - reserva/segundo time real: importado quando a fonte encontra um
            #   afiliado B/II/Reserva;
            # - base: importada do afiliado U20/U19/U18/U17, limitada a <=20 anos.
            affiliates = discover_affiliate_clubs(
                club_id,
                team["name"],
                spec.country_name,
                qa,
                name_variants=[
                    profile.get("shortName"),
                    profile.get("name"),
                    raw_club.get("name"),
                ],
            )

            reserve_players = []
            reserve_club = affiliates.get("reserve")
            if reserve_club:
                try:
                    reserve_payload = api_json(
                        f"/clubs/{reserve_club['id']}/players"
                    )
                    reserve_players = [
                        p for p in reserve_payload.get("players", [])
                        if isinstance(p, dict) and p.get("id")
                    ]
                except Exception:
                    reserve_players = []

            youth_players = []
            youth_club = affiliates.get("youth")
            if youth_club:
                try:
                    youth_payload = api_json(
                        f"/clubs/{youth_club['id']}/players"
                    )
                    for youth_raw in youth_payload.get("players", []):
                        if not isinstance(youth_raw, dict) or not youth_raw.get("id"):
                            continue
                        age = raw_player_age(youth_raw)
                        if age is None:
                            qa["youthPlayersSkippedUnknownAge"] += 1
                            continue
                        if age > 20:
                            qa["youthPlayersSkippedOver20"] += 1
                            continue
                        youth_players.append(youth_raw)
                except Exception:
                    youth_players = []
            else:
                qa["clubsWithoutYouthSource"].append({
                    "clubId": team["id"],
                    "clubName": team["name"],
                    "country": spec.country_code,
                })

            qa["squadSegments"][team["id"]] = {
                "clubName": team["name"],
                "seniorMainRoster": len(raw_players),
                "reserveAffiliateRoster": len(reserve_players),
                "youthBaseRoster": len(youth_players),
                "reserveAffiliateId": (
                    str(reserve_club["id"]) if reserve_club else None
                ),
                "youthAffiliateId": (
                    str(youth_club["id"]) if youth_club else None
                ),
            }

            if spec.division == 1 and club_id in competition_source_ids:
                if len(raw_players) < 18:
                    qa["playableSquadFailures"].append({
                        "clubId": team["id"],
                        "clubName": team["name"],
                        "country": spec.country_code,
                        "problems": [f"principal={len(raw_players)}"],
                    })

                if not youth_club or len(youth_players) < 12:
                    qa["youthBackfillRequired"].append({
                        "clubId": team["id"],
                        "clubName": team["name"],
                        "country": spec.country_code,
                        "realYouthPlayers": len(youth_players),
                        "targetYouthPlayers": 18,
                    })

            # ESPN entra somente nos clubes participantes da primeira divisao.
            # O cruzamento continua sendo por identidade (DOB+nome ou nome muito
            # forte dentro do mesmo clube), nunca por nome global.
            espn_photos = {}
            if spec.division == 1 and club_id in competition_source_ids:
                espn_photos = espn_photo_map(
                    team["name"],
                    spec.country_code,
                    raw_players,
                    qa,
                )

            if len(raw_players) < 14:
                qa["rosterWarnings"].append({
                    "clubId": team["id"],
                    "clubName": team["name"],
                    "country": spec.country_code,
                    "players": len(raw_players),
                })

            # Fotos do clube em paralelo; a identidade continua sendo o ID TM.
            main_player_ids = {str(p["id"]) for p in raw_players}

            def _photo_job(p: dict) -> tuple[str, str | None, str | None]:
                pid = f"tm-player-{p['id']}"
                path = download_asset(pid, p.get("imageUrl"), ASSETS_PLAYERS)
                source = "transfermarkt" if path else None
                if not path:
                    espn_url = espn_photos.get(str(p["id"]))
                    path = download_asset(pid, espn_url, ASSETS_PLAYERS)
                    source = "espn" if path else None
                if not path:
                    fallback_url = fotmob_player_photo(
                        p,
                        team["name"],
                        qa,
                    )
                    path = download_asset(pid, fallback_url, ASSETS_PLAYERS)
                    source = "fotmob" if path else None

                # Ultima tentativa para o elenco principal: consulta o perfil
                # Transfermarkt pelo MESMO ID do jogador. Nao ha matching por nome.
                if not path and str(p["id"]) in main_player_ids:
                    qa["profileFallbackRequests"] = qa.get("profileFallbackRequests", 0) + 1
                    try:
                        profile = api_json(f"/players/{p['id']}/profile")
                    except Exception:
                        profile = {}
                    profile_url = profile.get("imageUrl") or profile.get("image_url")
                    path = download_asset(pid, profile_url, ASSETS_PLAYERS)
                    if path:
                        source = "tm-profile"
                        qa["profileFallbackPhotos"] = qa.get("profileFallbackPhotos", 0) + 1

                return pid, path, source

            photo_paths: dict[str, str | None] = {}
            all_photo_players = {}
            for player_source in (raw_players, reserve_players, youth_players):
                for source_player in player_source:
                    all_photo_players[str(source_player["id"])] = source_player

            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = [
                    pool.submit(_photo_job, p)
                    for p in all_photo_players.values()
                ]
                for future in as_completed(futures):
                    pid, ppath, source = future.result()
                    photo_paths[pid] = ppath
                    if source == "fotmob":
                        qa["fotmobFallbackPhotos"] = qa.get("fotmobFallbackPhotos", 0) + 1
                    elif source == "espn":
                        qa["espnFallbackPhotos"] = qa.get("espnFallbackPhotos", 0) + 1

            for raw_player in raw_players:
                pid = f"tm-player-{raw_player['id']}"
                player = build_player(
                    raw_player,
                    team["id"],
                    spec.country_code,
                    club_value,
                    photo_paths.get(pid),
                )
                # Jogador emprestado/listado em dois elencos nao pode existir duas vezes.
                # Conservamos a primeira ocorrencia do ID e registramos o clube dela.
                if player["id"] not in players_by_id:
                    players_by_id[player["id"]] = player
                    comp_player_count += 1
                    qa["segmentStats"]["seniorMain"]["players"] += 1
                    if spec.division == 1 and club_id in competition_source_ids:
                        qa["segmentStats"]["topDivisionMain"]["players"] += 1
                    if player.get("photo"):
                        comp_photo_count += 1
                        qa["segmentStats"]["seniorMain"]["withPhotos"] += 1
                        if spec.division == 1 and club_id in competition_source_ids:
                            qa["segmentStats"]["topDivisionMain"]["withPhotos"] += 1
                    qa["positionCounts"][player["position"]] = qa["positionCounts"].get(player["position"], 0) + 1

            # Reserva/segundo time real entra no elenco senior do clube principal.
            for raw_player in reserve_players:
                pid = f"tm-player-{raw_player['id']}"
                if pid in players_by_id:
                    continue
                player = build_player(
                    raw_player,
                    team["id"],
                    spec.country_code,
                    club_value,
                    photo_paths.get(pid),
                )
                player["youth"] = False
                players_by_id[player["id"]] = player
                comp_player_count += 1
                qa["reservePlayersImported"] += 1
                qa["segmentStats"]["reserveAffiliate"]["players"] += 1
                if player.get("photo"):
                    comp_photo_count += 1
                    qa["segmentStats"]["reserveAffiliate"]["withPhotos"] += 1
                qa["positionCounts"][player["position"]] = qa["positionCounts"].get(player["position"], 0) + 1

            # Base real: nunca colocar jogador acima de 20 anos no plantel de base.
            for raw_player in youth_players:
                pid = f"tm-player-{raw_player['id']}"
                if pid in players_by_id:
                    # Se ja subiu e esta no elenco principal/reserva, preserva o
                    # registro senior; nao duplica nem rebaixa o atleta.
                    continue
                player = build_player(
                    raw_player,
                    team["id"],
                    spec.country_code,
                    club_value,
                    photo_paths.get(pid),
                )
                age = raw_player_age(raw_player)
                if age is None or age > 20:
                    continue
                player["youth"] = True
                players_by_id[player["id"]] = player
                comp_player_count += 1
                qa["youthPlayersImported"] += 1
                qa["segmentStats"]["youthBase"]["players"] += 1
                if player.get("photo"):
                    comp_photo_count += 1
                    qa["segmentStats"]["youthBase"]["withPhotos"] += 1
                qa["positionCounts"][player["position"]] = qa["positionCounts"].get(player["position"], 0) + 1

        competition_defs.append({
            "schema": "competition",
            "id": spec.key,
            "name": spec.display_name,
            "type": "League",
            "scope": "Domestic",
            "countryId": spec.country_code,
            "priority": spec.priority,
            "format": {"kind": "LeagueTable", "legs": spec.legs},
            "participants": {"explicit": participant_ids},
            "seasonStartMonth": 1 if spec.country_code in {"BR", "AR", "UY", "PY"} else 2,
            "seasonStartDay": 15,
        })

        qa["competitions"][spec.key] = {
            "sourceCompetitionId": str(remote_comp["id"]),
            "clubs": len(participant_ids),
            "newPlayers": comp_player_count,
            "playersWithPhotos": comp_photo_count,
            "clubsWithLogos": comp_logo_count,
        }
        country_qa = qa["countries"].setdefault(spec.country_code, {
            "name": spec.country_name, "clubs": 0, "players": 0, "competitions": []
        })
        country_qa["clubs"] = qa["countryCatalogCounts"].get(
            spec.country_code, country_qa["clubs"]
        )
        country_qa["players"] += comp_player_count
        country_qa["competitions"].append(spec.key)

    teams = list(teams_by_id.values())
    players = list(players_by_id.values())
    qa["clubsTotal"] = len(teams)
    qa["playersTotal"] = len(players)
    qa["playersWithPhotos"] = sum(1 for p in players if p.get("photo"))
    qa["clubsWithLogos"] = sum(1 for t in teams if t.get("logo"))

    # QA estrutural obrigatoria.
    if len({t["id"] for t in teams}) != len(teams):
        raise RuntimeError("QA: IDs duplicados de clubes.")

    catalog_total = sum(qa["countryCatalogCounts"].values())
    min_teams = max(1, int(catalog_total * 0.90))
    min_players = max(120, int(len(teams) * 10))
    qa["minimumExpectedTeams"] = min_teams
    qa["minimumExpectedPlayers"] = min_players
    if len(teams) < min_teams:
        raise RuntimeError(
            f"QA: poucos clubes enriquecidos: {len(teams)}/{catalog_total} catalogados"
        )
    if len(players) < min_players:
        raise RuntimeError(
            f"QA: poucos jogadores enriquecidos: {len(players)} para {len(teams)} clubes"
        )
    if len({p["id"] for p in players}) != len(players):
        raise RuntimeError("QA: IDs duplicados de jogadores.")

    team_ids = {t["id"] for t in teams}
    bad_player_clubs = [p["id"] for p in players if p["club"] not in team_ids]
    if bad_player_clubs:
        raise RuntimeError(f"QA: jogadores com clube inexistente: {bad_player_clubs[:10]}")

    overage_youth = []
    for player in players:
        if not player.get("youth"):
            continue
        dob = str(player.get("dateOfBirth") or "")[:10]
        age = player.get("age")
        if dob:
            try:
                born = datetime.strptime(dob, "%Y-%m-%d").date()
                anchor = date(2026, 1, 1)
                age = anchor.year - born.year - (
                    (anchor.month, anchor.day) < (born.month, born.day)
                )
            except Exception:
                pass
        try:
            age = int(age) if age is not None else None
        except Exception:
            age = None
        if age is not None and age > 20:
            overage_youth.append((player["id"], age))
    if overage_youth:
        raise RuntimeError(
            f"QA: jogadores acima de 20 anos na base: {overage_youth[:20]}"
        )

    qa["seniorPlayersTotal"] = sum(1 for p in players if not p.get("youth"))
    qa["youthPlayersTotal"] = sum(1 for p in players if p.get("youth"))
    qa["clubsWithYouthRoster"] = sum(
        1 for data in qa["squadSegments"].values()
        if data.get("youthBaseRoster", 0) > 0
    )
    qa["clubsWithReserveAffiliate"] = sum(
        1 for data in qa["squadSegments"].values()
        if data.get("reserveAffiliateRoster", 0) > 0
    )

    generic_positions = [
        p["id"] for p in players
        if p["position"] not in POSITION_DELTAS
    ]
    if generic_positions:
        raise RuntimeError(f"QA: posicoes nao mapeadas: {generic_positions[:10]}")

    photo_paths = [p["photo"] for p in players if p.get("photo")]
    if len(photo_paths) != len(set(photo_paths)):
        raise RuntimeError("QA: duas pessoas apontam para o mesmo arquivo de foto.")
    bad_photo_links = [
        (p["id"], p.get("photo"))
        for p in players if p.get("photo")
        and not Path(p["photo"]).stem == p["id"]
    ]
    if bad_photo_links:
        raise RuntimeError(f"QA ID->foto falhou: {bad_photo_links[:10]}")

    # Integridade visual por CONTEUDO, nao apenas por caminho. Alguns provedores
    # retornam a mesma silhueta/placeholder para IDs diferentes; isso nao pode
    # ser contado como foto real do atleta.
    photo_hashes: dict[str, list[str]] = {}
    missing_asset_files = []
    for player in players:
        photo = player.get("photo")
        if not photo:
            continue
        asset_path = ROOT / photo
        if not asset_path.exists():
            missing_asset_files.append(player["id"])
            player.pop("photo", None)
            continue
        digest = sha256(asset_path.read_bytes()).hexdigest()
        photo_hashes.setdefault(digest, []).append(player["id"])

    duplicate_content_groups = [
        ids for ids in photo_hashes.values() if len(ids) > 1
    ]
    duplicate_content_players = {
        player_id
        for group in duplicate_content_groups
        for player_id in group
    }
    if duplicate_content_players:
        for player in players:
            if player["id"] in duplicate_content_players:
                photo = player.pop("photo", None)
                if photo:
                    try:
                        (ROOT / photo).unlink(missing_ok=True)
                    except Exception:
                        pass

    qa["missingPhotoAssetFiles"] = missing_asset_files[:100]
    qa["duplicatePhotoContentGroups"] = duplicate_content_groups[:50]
    qa["duplicatePhotoContentPlayers"] = len(duplicate_content_players)
    qa["playersWithPhotos"] = sum(1 for p in players if p.get("photo"))

    logo_paths = [t["logo"] for t in teams if t.get("logo")]
    if len(logo_paths) != len(set(logo_paths)):
        raise RuntimeError("QA: logos de clubes duplicados por caminho.")

    photo_ratio = qa["playersWithPhotos"] / max(1, qa["playersTotal"])
    logo_ratio = qa["clubsWithLogos"] / max(1, qa["clubsTotal"])
    qa["photoCoverage"] = round(photo_ratio, 4)
    qa["logoCoverage"] = round(logo_ratio, 4)

    for segment_name, stats in qa["segmentStats"].items():
        stats["photoCoverage"] = round(
            stats["withPhotos"] / max(1, stats["players"]),
            4,
        )

    qa["transfermarktPhotos"] = max(
        0,
        qa["playersWithPhotos"]
        - qa.get("fotmobFallbackPhotos", 0)
        - qa.get("espnFallbackPhotos", 0),
    )
    missing_photo_ids = [p["id"] for p in players if not p.get("photo")]
    qa["missingRealPhotos"] = len(missing_photo_ids)
    qa["missingRealPhotoIdSample"] = missing_photo_ids[:100]

    # Grave sempre o snapshot de auditoria antes de uma trava de qualidade.
    # Assim um lote reprovado ainda informa exatamente o que falta corrigir.
    (QA_ROOT / "summary.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    qa["academyPolicy"] = {
        "realYouthImportedWhenAvailable": True,
        "runtimeBackfillTarget": 18,
        "maximumYouthAge": 20,
        "note": (
            "Clubes sem elenco de base publico suficiente recebem complemento "
            "procedural no runtime do CM; jogadores reais encontrados sao preservados."
        ),
    }

    top_photo = qa["segmentStats"]["topDivisionMain"]["photoCoverage"]
    qa["photoCoverageGate"] = {
        "topDivisionMainMinimum": 0.75,
        "overallRecordedNotFatal": True,
        "reason": (
            "Base/reserva de divisões menores nem sempre possui foto pública real; "
            "o CM não fabrica retratos para satisfazer cobertura."
        ),
    }

    if qa["playableSquadFailures"]:
        sample = qa["playableSquadFailures"][:20]
        raise RuntimeError(
            f"QA: elenco principal/base incompleto em clubes jogáveis: {sample}"
        )
    if qa["segmentStats"]["topDivisionMain"]["players"] and top_photo < 0.75:
        raise RuntimeError(
            "QA: fotos reais insuficientes no elenco principal da primeira divisão: "
            f"{top_photo:.1%}"
        )
    if logo_ratio < 0.90:
        raise RuntimeError(
            f"QA: cobertura de logos insuficiente: {qa['clubsWithLogos']}/{qa['clubsTotal']}"
        )

    selected_codes = [spec.country_code for spec in specs]
    unique_codes = list(dict.fromkeys(selected_codes))
    shard_code = unique_codes[0] if len(unique_codes) == 1 else None
    package_id = f"cm-{shard_code.lower()}-2026" if shard_code else "cm-south-america-2026"
    package_name = (
        f"CM {qa['countries'][shard_code]['name']} 2026"
        if shard_code
        else "CM America do Sul 2026"
    )

    manifest = {
        "schema": "world",
        "id": package_id,
        "name": package_name,
        "description": (
            "Base sul-americana por paises com clubes, elencos, fotos, logos, "
            "posicoes e dados biograficos reais; atributos calculados por modelo "
            "conceitual FM baseado em posicao, idade, altura e valor de mercado."
        ),
        "version": "1.0.0",
        "author": "CM",
        "license": "CC0-1.0",
        "packageType": "database",
        "gameMinVersion": "0.3.0",
        "formatVersion": 1,
        "baseYear": 2026,
        "defaultActiveRegions": [],
        "defaultActiveCompetitions": [spec.key for spec in specs if spec.division == 1],
    }

    (ROOT / "package.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "teams" / "teams.json").write_text(
        json.dumps({"schema": "team", "items": teams}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (ROOT / "players" / "players.json").write_text(
        json.dumps({"schema": "player", "items": players}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for comp in competition_defs:
        (ROOT / "competitions" / f"{comp['id']}.json").write_text(
            json.dumps(comp, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    (QA_ROOT / "summary.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n=== QA CONSOLIDADA ===")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return qa


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--countries",
        nargs="*",
        default=[],
        help="Codigos ISO dos paises a gerar. Vazio = todos.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    selected = {c.strip().upper() for c in args.countries if c.strip()} or None
    summary = generate(selected)
    print(ROOT)
    print(
        f"OK: {summary['clubsTotal']} clubes, {summary['playersTotal']} jogadores, "
        f"{summary['photoCoverage']:.1%} fotos, {summary['logoCoverage']:.1%} logos."
    )
