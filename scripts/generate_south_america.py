from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
from io import BytesIO
from math import log10
from pathlib import Path
from urllib.parse import quote, urlparse
import argparse
import json
import random
import re
import shutil
import time
import unicodedata
import urllib.request

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit("Pillow is required: python -m pip install pillow") from exc

ROOT = Path("wfe-south-america")
ASSETS_PLAYERS = ROOT / "assets" / "players" / "by-id"
ASSETS_CLUBS = ROOT / "assets" / "clubs" / "by-id"
TM_BASE = "https://transfermarkt-api.fly.dev"
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/140 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}

# O endpoint publico usado aqui informa limite de 2 requests a cada 3 segundos.
# Esta cadencia deixa a geracao previsivel e evita martelar a fonte.
_last_api_request_at = 0.0


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


COMPETITIONS: tuple[CompetitionSpec, ...] = (
    CompetitionSpec(
        "arg-primera", "AR", "Argentina", "Liga Profesional Argentina",
        ("Liga Profesional", "Primera Division Argentina", "Primera División Argentina"),
        10, 2, 20,
    ),
    CompetitionSpec(
        "bol-primera", "BO", "Bolivia", "Division Profesional Bolivia",
        ("Division Profesional", "División Profesional", "Primera Division Bolivia"),
        10, 2, 14,
    ),
    CompetitionSpec(
        "bra-serie-a", "BR", "Brazil", "Campeonato Brasileiro Serie A",
        ("Campeonato Brasileiro Serie A", "Brasileirao Serie A", "Brasileirão Série A"),
        10, 2, 18,
    ),
    CompetitionSpec(
        "bra-serie-b", "BR", "Brazil", "Campeonato Brasileiro Serie B",
        ("Campeonato Brasileiro Serie B", "Brasileirao Serie B", "Brasileirão Série B"),
        20, 2, 18, 2,
    ),
    CompetitionSpec(
        "bra-serie-c", "BR", "Brazil", "Campeonato Brasileiro Serie C",
        ("Campeonato Brasileiro Serie C", "Brasileirao Serie C", "Brasileirão Série C"),
        30, 1, 18, 3,
    ),
    CompetitionSpec(
        "chi-primera", "CL", "Chile", "Primera Division de Chile",
        ("Primera Division de Chile", "Primera División de Chile", "Primera Division Chile"),
        10, 2, 14,
    ),
    CompetitionSpec(
        "col-primera-a", "CO", "Colombia", "Primera A Colombia",
        ("Primera A Colombia", "Liga Dimayor", "Categoria Primera A"),
        10, 2, 18,
    ),
    CompetitionSpec(
        "ecu-serie-a", "EC", "Ecuador", "LigaPro Serie A",
        ("LigaPro Serie A", "Serie A Ecuador", "Primera Etapa Ecuador"),
        10, 2, 14,
    ),
    CompetitionSpec(
        "par-primera", "PY", "Paraguay", "Primera Division Paraguay",
        ("Primera Division Paraguay", "Primera División Paraguay", "Division Profesional Paraguay"),
        10, 2, 10,
    ),
    CompetitionSpec(
        "per-liga-1", "PE", "Peru", "Liga 1 Peru",
        ("Liga 1 Peru", "Liga 1", "Primera Division Peru"),
        10, 2, 16,
    ),
    CompetitionSpec(
        "uru-primera", "UY", "Uruguay", "Primera Division Uruguay",
        ("Primera Division Uruguay", "Primera División Uruguay", "Liga AUF Uruguaya"),
        10, 2, 14,
    ),
    CompetitionSpec(
        "ven-primera", "VE", "Venezuela", "Liga FUTVE",
        ("Liga FUTVE", "Primera Division Venezuela", "Primera División Venezuela"),
        10, 2, 12,
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
    elapsed = time.monotonic() - _last_api_request_at
    if elapsed < 1.60:
        time.sleep(1.60 - elapsed)

    url = path if path.startswith("http") else TM_BASE + path
    last_error = None
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


def resolve_competition(spec: CompetitionSpec) -> dict:
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
    (ROOT / "teams").mkdir(parents=True)
    (ROOT / "players").mkdir(parents=True)
    (ROOT / "competitions").mkdir(parents=True)
    ASSETS_PLAYERS.mkdir(parents=True)
    ASSETS_CLUBS.mkdir(parents=True)
    (ROOT / "qa").mkdir(parents=True)


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
    qa = {
        "countries": {},
        "competitions": {},
        "clubsTotal": 0,
        "playersTotal": 0,
        "playersWithPhotos": 0,
        "clubsWithLogos": 0,
        "positionCounts": {},
        "source": "Transfermarkt public JSON API",
        "attributeModel": "FM-style conceptual role weights over real market/biographical data; no proprietary FM database copied",
    }

    for spec in specs:
        print(f"\n=== LOTE PAIS {spec.country_code} / {spec.display_name} ===")
        remote_comp = resolve_competition(spec)
        clubs_payload = api_json(f"/competitions/{remote_comp['id']}/clubs")
        raw_clubs = clubs_payload.get("clubs", [])
        if len(raw_clubs) < spec.min_clubs:
            raise RuntimeError(
                f"{spec.key}: apenas {len(raw_clubs)} clubes; minimo esperado {spec.min_clubs}"
            )

        participant_ids: list[str] = []
        comp_player_count = 0
        comp_photo_count = 0
        comp_logo_count = 0

        for index, raw_club in enumerate(raw_clubs, start=1):
            club_id = str(raw_club.get("id") or "").strip()
            if not club_id:
                continue
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
            participant_ids.append(team["id"])
            club_value = profile.get("currentMarketValue")

            raw_players = [
                p for p in roster.get("players", [])
                if isinstance(p, dict) and p.get("id")
            ]
            if len(raw_players) < 14:
                raise RuntimeError(
                    f"{team['name']}: elenco atual muito pequeno ({len(raw_players)})"
                )

            # Fotos do clube em paralelo; a identidade continua sendo o ID TM.
            def _photo_job(p: dict) -> tuple[str, str | None]:
                pid = f"tm-player-{p['id']}"
                path = download_asset(pid, p.get("imageUrl"), ASSETS_PLAYERS)
                return pid, path

            photo_paths: dict[str, str | None] = {}
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = [pool.submit(_photo_job, p) for p in raw_players]
                for future in as_completed(futures):
                    pid, ppath = future.result()
                    photo_paths[pid] = ppath

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
                    if player.get("photo"):
                        comp_photo_count += 1
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
        country_qa["clubs"] += len(participant_ids)
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
    if len({p["id"] for p in players}) != len(players):
        raise RuntimeError("QA: IDs duplicados de jogadores.")

    team_ids = {t["id"] for t in teams}
    bad_player_clubs = [p["id"] for p in players if p["club"] not in team_ids]
    if bad_player_clubs:
        raise RuntimeError(f"QA: jogadores com clube inexistente: {bad_player_clubs[:10]}")

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

    logo_paths = [t["logo"] for t in teams if t.get("logo")]
    if len(logo_paths) != len(set(logo_paths)):
        raise RuntimeError("QA: logos de clubes duplicados por caminho.")

    photo_ratio = qa["playersWithPhotos"] / max(1, qa["playersTotal"])
    logo_ratio = qa["clubsWithLogos"] / max(1, qa["clubsTotal"])
    qa["photoCoverage"] = round(photo_ratio, 4)
    qa["logoCoverage"] = round(logo_ratio, 4)
    if photo_ratio < 0.85:
        raise RuntimeError(
            f"QA: cobertura de fotos insuficiente: {qa['playersWithPhotos']}/{qa['playersTotal']}"
        )
    if logo_ratio < 0.90:
        raise RuntimeError(
            f"QA: cobertura de logos insuficiente: {qa['clubsWithLogos']}/{qa['clubsTotal']}"
        )

    manifest = {
        "schema": "world",
        "id": "cm-south-america-2026",
        "name": "CM America do Sul 2026",
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
    (ROOT / "qa" / "summary.json").write_text(
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
