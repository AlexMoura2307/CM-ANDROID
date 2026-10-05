from pathlib import Path
from datetime import datetime, timezone
from difflib import SequenceMatcher
from urllib.parse import quote, urlparse
import json, shutil, time, unicodedata, urllib.request

root = Path("wfe-brasil-fase1")
if root.exists():
    shutil.rmtree(root)
(root/"teams").mkdir(parents=True)
(root/"competitions").mkdir(parents=True)
(root/"players").mkdir(parents=True)
(root/"assets"/"players").mkdir(parents=True)

A = [
("athletico-pr","Athletico Paranaense","CAP","Curitiba","#d71920","#000000"),
("atletico-mg","Atlético Mineiro","CAM","Belo Horizonte","#111111","#ffffff"),
("bahia","Bahia","BAH","Salvador","#0057b8","#e31b23"),
("botafogo-rj","Botafogo","BOT","Rio de Janeiro","#000000","#ffffff"),
("chapecoense","Chapecoense","CHA","Chapecó","#008f4c","#ffffff"),
("corinthians","Corinthians","COR","São Paulo","#111111","#ffffff"),
("coritiba","Coritiba","CFC","Curitiba","#006b3c","#ffffff"),
("cruzeiro","Cruzeiro","CRU","Belo Horizonte","#1746a2","#ffffff"),
("flamengo","Flamengo","FLA","Rio de Janeiro","#d71920","#111111"),
("fluminense","Fluminense","FLU","Rio de Janeiro","#7a1538","#006b3c"),
("gremio","Grêmio","GRE","Porto Alegre","#55a9e2","#000000"),
("internacional","Internacional","INT","Porto Alegre","#d71920","#ffffff"),
("mirassol","Mirassol","MIR","Mirassol","#f7d117","#1b8f3a"),
("palmeiras","Palmeiras","PAL","São Paulo","#006437","#ffffff"),
("red-bull-bragantino","Red Bull Bragantino","RBB","Bragança Paulista","#ffffff","#d71920"),
("remo","Remo","REM","Belém","#003c8f","#ffffff"),
("santos","Santos FC","SAN","Santos","#ffffff","#111111"),
("sao-paulo","São Paulo","SAO","São Paulo","#ffffff","#d71920"),
("vasco","Vasco da Gama","VAS","Rio de Janeiro","#111111","#ffffff"),
("vitoria","Vitória","VIT","Salvador","#d71920","#111111"),
]
B = [
("criciuma","Criciúma","CRI","Criciúma","#f3d21b","#111111"),
("operario-pr","Operário","OPE","Ponta Grossa","#111111","#ffffff"),
("vila-nova","Vila Nova","VIL","Goiânia","#d71920","#ffffff"),
("juventude","Juventude","JUV","Caxias do Sul","#178447","#ffffff"),
("fortaleza","Fortaleza","FOR","Fortaleza","#1746a2","#d71920"),
("novorizontino","Novorizontino","NOV","Novo Horizonte","#f3d21b","#111111"),
("goias","Goiás","GOI","Goiânia","#178447","#ffffff"),
("atletico-go","Atlético Goianiense","ACG","Goiânia","#d71920","#111111"),
("sport","Sport Recife","SPT","Recife","#d71920","#111111"),
("sao-bernardo","São Bernardo","SBE","São Bernardo do Campo","#f3d21b","#111111"),
("athletic-mg","Athletic Club","ATH","São João del-Rei","#111111","#ffffff"),
("crb","CRB","CRB","Maceió","#d71920","#ffffff"),
("nautico","Náutico","NAU","Recife","#d71920","#ffffff"),
("botafogo-sp","Botafogo-SP","BSP","Ribeirão Preto","#d71920","#111111"),
("cuiaba","Cuiabá","CUI","Cuiabá","#f3d21b","#178447"),
("londrina","Londrina","LON","Londrina","#1746a2","#ffffff"),
("avai","Avaí","AVA","Florianópolis","#1746a2","#ffffff"),
("ceara","Ceará","CEA","Fortaleza","#111111","#ffffff"),
("ponte-preta","Ponte Preta","PON","Campinas","#111111","#ffffff"),
("america-mg","América Mineiro","AME","Belo Horizonte","#178447","#ffffff"),
]
C = [
("brusque","Brusque","BRU","Brusque","#f3d21b","#d71920"),
("caxias","Caxias","CAX","Caxias do Sul","#7a1538","#ffffff"),
("ypiranga-rs","Ypiranga-RS","YPI","Erechim","#178447","#f3d21b"),
("figueirense","Figueirense","FIG","Florianópolis","#111111","#ffffff"),
("botafogo-pb","Botafogo-PB","BPB","João Pessoa","#111111","#ffffff"),
("barra-sc","Barra FC","BAR","Itajaí","#1746a2","#f3d21b"),
("maringa","Maringá FC","MAR","Maringá","#111111","#178447"),
("maranhao","Maranhão","MAC","São Luís","#1746a2","#d71920"),
("paysandu","Paysandu","PAY","Belém","#1746a2","#ffffff"),
("confianca","Confiança","CON","Aracaju","#1746a2","#ffffff"),
("anapolis","Anápolis","ANA","Anápolis","#1746a2","#ffffff"),
("inter-limeira","Inter de Limeira","ITL","Limeira","#111111","#ffffff"),
("volta-redonda","Volta Redonda","VRE","Volta Redonda","#f3d21b","#111111"),
("amazonas","Amazonas","AMZ","Manaus","#f3d21b","#111111"),
("ferroviaria","Ferroviária","FER","Araraquara","#7a1538","#ffffff"),
("itabaiana","Itabaiana","ITA","Itabaiana","#1746a2","#ffffff"),
("guarani","Guarani","GUA","Campinas","#178447","#ffffff"),
("santa-cruz","Santa Cruz","SCZ","Recife","#111111","#d71920"),
("floresta","Floresta","FLO","Fortaleza","#178447","#ffffff"),
("ituano","Ituano","ITU","Itu","#d71920","#111111"),
]

def team(x, rep, fin):
    i,n,s,c,p,q=x
    return {"id":i,"name":n,"shortName":s,"city":c,"country":"BR",
            "colors":{"primary":p,"secondary":q},"playStyle":"Balanced",
            "reputationRange":rep,"financeRange":fin}

teams=[team(x,[650,900],[5000000,25000000]) for x in A]+[team(x,[450,700],[2000000,12000000]) for x in B]+[team(x,[300,550],[800000,6000000]) for x in C]


# Elencos reais da Serie A 2026.
# ESPN e a fonte de identidade/elenco. Transfermarkt enriquece cada atleta com
# posicao especifica e foto real. As fotos sao baixadas no build e empacotadas
# localmente, para o APK nao depender de links externos durante o jogo.
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1"
TRANSFERMARKT_BASE = "https://transfermarkt-api.fly.dev"

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/140 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}

def _http_json_url(url):
    last_error = None
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers=HTTP_HEADERS)
            with urllib.request.urlopen(request, timeout=35) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            time.sleep(2 + attempt * 2)
    raise RuntimeError(f"Fonte de dados indisponivel para {url}: {last_error}")

def _http_bytes_url(url):
    last_error = None
    headers = dict(HTTP_HEADERS)
    headers["Accept"] = "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
                if len(data) < 512:
                    raise RuntimeError("imagem vazia ou invalida")
                return data
        except Exception as exc:
            last_error = exc
            time.sleep(1 + attempt * 2)
    return None

def _norm(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(
        "".join(ch if ch.isalnum() else " " for ch in value.lower()).split()
    )

ESPN_ALIASES = {
    "athletico-pr": ["athletico paranaense", "athletico pr", "athletico"],
    "atletico-mg": ["atletico mineiro", "atletico mg"],
    "bahia": ["bahia", "ec bahia"],
    "botafogo-rj": ["botafogo", "botafogo rj"],
    "chapecoense": ["chapecoense"],
    "corinthians": ["corinthians", "sc corinthians paulista"],
    "coritiba": ["coritiba", "coritiba fc"],
    "cruzeiro": ["cruzeiro"],
    "flamengo": ["flamengo", "cr flamengo"],
    "fluminense": ["fluminense", "fluminense fc"],
    "gremio": ["gremio", "gremio fbpa"],
    "internacional": ["internacional", "sc internacional"],
    "mirassol": ["mirassol", "mirassol fc"],
    "palmeiras": ["palmeiras", "se palmeiras"],
    "red-bull-bragantino": ["red bull bragantino", "rb bragantino", "bragantino"],
    "remo": ["remo", "clube do remo"],
    "santos": ["santos", "santos fc"],
    "sao-paulo": ["sao paulo", "sao paulo fc"],
    "vasco": ["vasco da gama", "vasco"],
    "vitoria": ["vitoria", "ec vitoria"],
}

TEAM_OVR_BASE = {
    "flamengo": 81, "palmeiras": 81, "athletico-pr": 76, "fluminense": 77,
    "bahia": 77, "cruzeiro": 76, "atletico-mg": 76, "santos": 74,
    "red-bull-bragantino": 74, "sao-paulo": 75, "botafogo-rj": 74,
    "corinthians": 74, "internacional": 74, "gremio": 73, "vasco": 73,
    "mirassol": 71, "coritiba": 71, "vitoria": 71, "chapecoense": 69, "remo": 69,
}

def _espn_teams(payload):
    try:
        entries = payload["sports"][0]["leagues"][0]["teams"]
    except (KeyError, IndexError, TypeError):
        entries = payload.get("teams", [])
    result = []
    for entry in entries:
        team = entry.get("team") if isinstance(entry, dict) else None
        result.append(team or entry)
    return [team for team in result if isinstance(team, dict) and team.get("id")]

def _espn_roster_items(payload):
    result = []
    for group in payload.get("athletes", []):
        if isinstance(group, dict) and isinstance(group.get("items"), list):
            result.extend(group["items"])
        elif isinstance(group, dict) and group.get("id"):
            result.append(group)
    return result

def _birth_date(player):
    raw = player.get("birthDate") or player.get("dateOfBirth")
    if isinstance(raw, str) and len(raw) >= 10:
        return raw[:10]
    return None

def _age_from_player(player, birth):
    if birth:
        try:
            born = datetime.strptime(birth, "%Y-%m-%d").date()
            return max(15, 2026 - born.year)
        except Exception:
            pass
    try:
        return int(player.get("age") or 25)
    except Exception:
        return 25

def _position(player):
    position = player.get("position") or {}
    raw = str(
        (position.get("abbreviation") if isinstance(position, dict) else "")
        or (position.get("name") if isinstance(position, dict) else "")
        or player.get("position")
        or ""
    ).strip().upper().replace("-", "").replace("_", "")
    exact = {
        "G": "Goalkeeper", "GK": "Goalkeeper", "GOALKEEPER": "Goalkeeper",
        "D": "Defender", "DEF": "Defender", "DEFENDER": "Defender",
        "CB": "CenterBack", "DC": "CenterBack", "CENTREBACK": "CenterBack", "CENTERBACK": "CenterBack",
        "LB": "LeftBack", "DL": "LeftBack", "LEFTBACK": "LeftBack",
        "RB": "RightBack", "DR": "RightBack", "RIGHTBACK": "RightBack",
        "M": "Midfielder", "MID": "Midfielder", "MIDFIELDER": "Midfielder",
        "DM": "DefensiveMidfielder", "DMC": "DefensiveMidfielder",
        "CM": "CentralMidfielder", "MC": "CentralMidfielder", "CENTRALMIDFIELDER": "CentralMidfielder",
        "AM": "AttackingMidfielder", "AMC": "AttackingMidfielder",
        "LM": "LeftMidfielder", "ML": "LeftMidfielder",
        "RM": "RightMidfielder", "MR": "RightMidfielder",
        "F": "Forward", "FW": "Forward", "FORWARD": "Forward",
        "LW": "LeftWinger", "AML": "LeftWinger",
        "RW": "RightWinger", "AMR": "RightWinger",
        "ST": "Striker", "CF": "Striker", "STRIKER": "Striker",
    }
    return exact.get(raw, "Midfielder")

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
}

SPECIFIC_POSITIONS = set(TM_POSITION_MAP.values())

def _tm_position(value):
    key = _norm(str(value or "").replace("-", " "))
    return TM_POSITION_MAP.get(key)

def _tm_foot(value):
    key = _norm(str(value or ""))
    if key in {"left", "esquerdo", "esquerda"}:
        return "Left"
    if key in {"both", "ambidextrous", "ambidestro"}:
        return "Both"
    if key:
        return "Right"
    return None

def _tm_find_club(team_id, team_name):
    aliases = [team_name] + ESPN_ALIASES.get(team_id, [])
    alias_norms = {_norm(value) for value in aliases if value}
    best = None
    best_score = -1.0
    seen_queries = set()
    for query_text in aliases:
        query_key = _norm(query_text)
        if not query_key or query_key in seen_queries:
            continue
        seen_queries.add(query_key)
        try:
            payload = _http_json_url(
                TRANSFERMARKT_BASE + "/clubs/search/" + quote(query_text, safe="")
            )
        except Exception:
            continue
        for candidate in payload.get("results", []):
            name = candidate.get("name") or ""
            country = _norm(candidate.get("country") or "")
            candidate_norm = _norm(name)
            if not candidate.get("id") or not candidate_norm:
                continue
            if country and country not in {"brazil", "brasil"}:
                continue
            if candidate_norm in alias_norms:
                score = 1.0
            else:
                score = max(
                    SequenceMatcher(None, candidate_norm, alias).ratio()
                    for alias in alias_norms
                )
            if score > best_score:
                best = candidate
                best_score = score
        if best_score >= 0.98:
            break
    if best is None or best_score < 0.58:
        return None
    return best

def _tm_players_for_team(team_id, team_name):
    club = _tm_find_club(team_id, team_name)
    if club is None:
        return []
    try:
        payload = _http_json_url(
            TRANSFERMARKT_BASE + f"/clubs/{club['id']}/players"
        )
    except Exception:
        return []
    return [p for p in payload.get("players", []) if isinstance(p, dict) and p.get("id")]

def _match_tm_player(player, tm_players):
    espn_name = _norm(
        player.get("displayName")
        or player.get("fullName")
        or player.get("name")
        or ""
    )
    if not espn_name:
        return None

    # 1. Nome exato normalizado.
    exact = [p for p in tm_players if _norm(p.get("name") or "") == espn_name]
    if exact:
        return exact[0]

    # 2. Data de nascimento e semelhanca de nome.
    birth = _birth_date(player)
    if birth:
        born = [
            p for p in tm_players
            if str(p.get("dateOfBirth") or "")[:10] == birth
        ]
        if born:
            return max(
                born,
                key=lambda p: SequenceMatcher(
                    None, espn_name, _norm(p.get("name") or "")
                ).ratio(),
            )

    # 3. Fallback somente por semelhanca MUITO forte dentro do mesmo clube.
    # Evita associar foto/posicao de um homonimo ao ID de outro jogador.
    scored = []
    for candidate in tm_players:
        tm_name = _norm(candidate.get("name") or "")
        if not tm_name:
            continue
        ratio = SequenceMatcher(None, espn_name, tm_name).ratio()
        espn_tokens = set(espn_name.split())
        tm_tokens = set(tm_name.split())
        overlap = len(espn_tokens & tm_tokens) / max(1, min(len(espn_tokens), len(tm_tokens)))
        scored.append((ratio, overlap, candidate))
    if not scored:
        return None
    ratio, overlap, candidate = max(scored, key=lambda item: (item[0], item[1]))
    if ratio >= 0.90 or (ratio >= 0.84 and overlap >= 0.80):
        return candidate
    return None

def _tm_identity_is_strong(espn_player, tm_player):
    if not tm_player:
        return False
    espn_name = _norm(
        espn_player.get("displayName")
        or espn_player.get("fullName")
        or espn_player.get("name")
        or ""
    )
    tm_name = _norm(tm_player.get("name") or "")
    if espn_name and tm_name and espn_name == tm_name:
        return True

    espn_birth = _birth_date(espn_player)
    tm_birth = str(tm_player.get("dateOfBirth") or "")[:10]
    if espn_birth and tm_birth and espn_birth == tm_birth:
        similarity = SequenceMatcher(None, espn_name, tm_name).ratio()
        return similarity >= 0.50

    return False

def _photo_extension(url):
    ext = urlparse(url).path.rsplit(".", 1)
    if len(ext) == 2:
        suffix = "." + ext[1].lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            return suffix
    return ".jpg"

def _download_player_photo(player_id, *urls):
    # A foto pertence ao ID estavel do jogador, nunca ao nome e nunca ao clube.
    # Assim uma transferencia de clube ou jogadores homonimos nao trocam retratos.
    safe_player_id = str(player_id).strip()
    if not safe_player_id:
        return None
    for url in urls:
        if not url:
            continue
        data = _http_bytes_url(str(url))
        if not data:
            continue
        rel = f"assets/players/by-id/{safe_player_id}{_photo_extension(str(url))}"
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return rel
    return None

NATION_CODE_MAP = {
    "BRA": "BR", "ARG": "AR", "URU": "UY", "COL": "CO", "PAR": "PY", "PRY": "PY",
    "CHI": "CL", "CHL": "CL", "ECU": "EC", "VEN": "VE", "PER": "PE", "BOL": "BO",
    "USA": "US", "CAN": "CA", "MEX": "MX", "CRC": "CR", "PAN": "PA", "DOM": "DO",
    "GHA": "GH", "NGA": "NG", "CMR": "CM", "SEN": "SN", "CIV": "CI", "MAR": "MA",
    "ALG": "DZ", "TUN": "TN", "EGY": "EG", "RSA": "ZA", "CPV": "CV", "ANG": "AO",
    "JPN": "JP", "KOR": "KR", "CHN": "CN", "AUS": "AU", "NZL": "NZ",
    "POR": "PT", "ESP": "ES", "FRA": "FR", "GER": "DE", "DEU": "DE", "ITA": "IT",
    "BEL": "BE", "NED": "NL", "NLD": "NL", "SUI": "CH", "CHE": "CH", "AUT": "AT",
    "POL": "PL", "CRO": "HR", "HRV": "HR", "SRB": "RS", "BIH": "BA", "SLO": "SI",
    "SVN": "SI", "SVK": "SK", "CZE": "CZ", "HUN": "HU", "ROU": "RO", "BUL": "BG",
    "GRE": "GR", "GRC": "GR", "TUR": "TR", "UKR": "UA", "RUS": "RU", "DEN": "DK",
    "DNK": "DK", "NOR": "NO", "SWE": "SE", "FIN": "FI", "ISL": "IS",
    # As nacoes britanicas usam os codigos futebolisticos que o WFE reconhece.
    "ENG": "ENG", "SCO": "SCO", "WAL": "WAL", "NIR": "NIR",
}

def _normalise_nation_code(value):
    code = str(value or "").strip().upper()
    if not code:
        return "BR"
    if len(code) == 2:
        return code
    return NATION_CODE_MAP.get(code, "BR")

def _nationality(player):
    for key in ("citizenship", "nationality"):
        raw = player.get(key)
        if isinstance(raw, str) and 2 <= len(raw) <= 3:
            return _normalise_nation_code(raw)
        if isinstance(raw, dict):
            code = raw.get("alpha2") or raw.get("abbreviation") or raw.get("code")
            if code:
                return _normalise_nation_code(code)
    birth_place = player.get("birthPlace") or {}
    if isinstance(birth_place, dict):
        country = birth_place.get("country")
        if isinstance(country, str) and 2 <= len(country) <= 3:
            return _normalise_nation_code(country)
    return "BR"

def _names(player):
    name = (player.get("displayName") or player.get("fullName") or player.get("name") or "Jogador").strip()
    first = (player.get("firstName") or "").strip()
    last = (player.get("lastName") or "").strip()
    bits = name.split()
    if not first:
        first = bits[0] if bits else name
    if not last:
        last = " ".join(bits[1:]) if len(bits) > 1 else first
    return name, first, last

def _rating(team_id, player_id, age):
    base = TEAM_OVR_BASE.get(team_id, 72)
    jitter = ((int(player_id) * 37) % 9) - 4
    age_adj = -3 if age <= 19 else (-1 if age >= 34 else 0)
    return max(58, min(85, base + jitter + age_adj))

def _potential(overall, age, player_id):
    if age <= 18:
        bonus = 8 + (int(player_id) % 5)
    elif age <= 21:
        bonus = 5 + (int(player_id) % 4)
    elif age <= 24:
        bonus = 2 + (int(player_id) % 3)
    else:
        bonus = 0
    return max(overall, min(92, overall + bonus))

def fetch_real_serie_a_players():
    teams_payload = _http_json_url(ESPN_BASE + "/teams")
    espn_teams = {
        _norm(team.get("displayName") or team.get("name")): team
        for team in _espn_teams(teams_payload)
    }

    results = []
    counts = {}
    matched_positions = {}
    matched_photos = {}
    missing = []

    for team_id, team_name, *_ in A:
        found = None
        aliases = [_norm(value) for value in ESPN_ALIASES.get(team_id, [])]
        for alias in aliases:
            if alias in espn_teams:
                found = espn_teams[alias]
                break
        if found is None:
            for key, team in espn_teams.items():
                if any(alias in key or key in alias for alias in aliases if len(alias) >= 5):
                    found = team
                    break
        if found is None:
            missing.append(team_id)
            continue

        payload = _http_json_url(ESPN_BASE + f"/teams/{found['id']}/roster")
        tm_players = _tm_players_for_team(team_id, team_name)

        seen = set()
        specific_count = 0
        photo_count = 0

        for player in _espn_roster_items(payload):
            player_id = player.get("id")
            if not player_id or str(player_id) in seen:
                continue
            seen.add(str(player_id))

            birth = _birth_date(player)
            age = _age_from_player(player, birth)
            display_name, first, last = _names(player)
            overall = _rating(team_id, player_id, age)

            tm_player = _match_tm_player(player, tm_players)
            tm_position = _tm_position(tm_player.get("position")) if tm_player else None
            position = tm_position or _position(player)
            if tm_position in SPECIFIC_POSITIONS:
                specific_count += 1

            headshot = player.get("headshot") or {}
            espn_headshot = headshot.get("href") if isinstance(headshot, dict) else None
            tm_photo = (
                tm_player.get("imageUrl")
                if _tm_identity_is_strong(player, tm_player)
                else None
            )
            internal_player_id = f"espn-{player_id}"
            # A fonte primaria da foto e a propria ESPN, no MESMO registro que
            # fornece o ID interno. Transfermarkt entra apenas como fallback
            # quando nome/data confirmam que se trata da mesma pessoa.
            photo = _download_player_photo(
                internal_player_id,
                espn_headshot,
                tm_photo,
            )
            if photo:
                photo_count += 1

            item = {
                "id": internal_player_id,
                "name": display_name,
                "firstName": first,
                "lastName": last,
                "club": team_id,
                "nationality": _nationality(player),
                "position": position,
                "overall": overall,
                "potential": _potential(overall, age, player_id),
                "youth": False,
            }

            if tm_player:
                foot = _tm_foot(tm_player.get("foot"))
                if foot:
                    item["footedness"] = foot
                value = tm_player.get("marketValue")
                if isinstance(value, int) and value >= 0:
                    item["value"] = value

            if photo:
                item["photo"] = photo

            if birth:
                item["dateOfBirth"] = birth
            else:
                item["age"] = age

            results.append(item)

        counts[team_id] = len(seen)
        matched_positions[team_id] = specific_count
        matched_photos[team_id] = photo_count
        time.sleep(0.10)

    if missing:
        raise RuntimeError("Times da Serie A nao encontrados na ESPN: " + ", ".join(missing))

    too_small = {team_id: count for team_id, count in counts.items() if count < 15}
    if too_small:
        raise RuntimeError(f"Elencos reais incompletos na ESPN: {too_small}")

    if len(results) < 360:
        raise RuntimeError(f"Poucos jogadores reais coletados para Serie A: {len(results)}")

    # QA: nao gerar novo APK com as posicoes voltando ao modelo generico.
    weak_positions = {
        team_id: f"{matched_positions.get(team_id, 0)}/{count}"
        for team_id, count in counts.items()
        if count and matched_positions.get(team_id, 0) / count < 0.70
    }
    if weak_positions:
        raise RuntimeError(
            "Transfermarkt nao confirmou posicoes especificas suficientes: "
            + str(weak_positions)
        )

    total_photos = sum(matched_photos.values())
    if total_photos < int(len(results) * 0.70):
        raise RuntimeError(
            f"Poucas fotos reais baixadas: {total_photos}/{len(results)}"
        )

    # Integridade global: um ID so pode pertencer a um jogador na base inteira.
    player_ids = [item["id"] for item in results]
    if len(player_ids) != len(set(player_ids)):
        duplicates = sorted({pid for pid in player_ids if player_ids.count(pid) > 1})
        raise RuntimeError(
            "IDs de jogadores duplicados na Serie A: " + ", ".join(duplicates[:10])
        )

    # Integridade ID -> foto: cada foto precisa estar amarrada ao ID do proprio
    # jogador e nenhum caminho pode ser reutilizado por dois atletas.
    photo_paths = []
    invalid_photo_links = []
    for item in results:
        photo = item.get("photo")
        if not photo:
            continue
        expected_prefix = f"assets/players/by-id/{item['id']}."
        if not photo.startswith(expected_prefix):
            invalid_photo_links.append((item["id"], photo))
        photo_paths.append(photo)
    duplicate_photo_paths = len(photo_paths) != len(set(photo_paths))
    if invalid_photo_links or duplicate_photo_paths:
        raise RuntimeError(
            "Falha de integridade ID->foto: "
            f"invalidos={invalid_photo_links[:5]}, duplicados={duplicate_photo_paths}"
        )

    print("WFE Brasil: jogadores reais Serie A =", len(results))
    print("WFE Brasil: atletas por clube =", counts)
    print("WFE Brasil: posicoes especificas =", matched_positions)
    print("WFE Brasil: fotos reais locais =", matched_photos)
    return results

real_serie_a_players = fetch_real_serie_a_players()

manifest={
 "schema":"world","id":"wfe-brasil-2026-fase1","name":"WFE Brasil 2026 - Fase 1",
 "description":"Base WFE Brasil com Series A, B e C, copas nacionais, elencos reais da Serie A 2026, posicoes especificas e fotos reais locais.",
 "version":"0.3.2","author":"WFE","license":"CC0-1.0","packageType":"database",
 "gameMinVersion":"0.3.0","formatVersion":1,"baseYear":2026,
 "defaultActiveRegions":[],"defaultActiveCompetitions":["br-serie-a","br-serie-b","br-serie-c","br-copa-do-brasil","br-supercopa"]
}

a=[x[0] for x in A]; b=[x[0] for x in B]; c=[x[0] for x in C]
comps=[
{"schema":"competition","id":"br-serie-a","name":"Campeonato Brasileiro Serie A","type":"League","scope":"Domestic","countryId":"BR","priority":10,"format":{"kind":"LeagueTable","legs":2},"participants":{"explicit":a},"seasonStartMonth":1,"seasonStartDay":28},
{"schema":"competition","id":"br-serie-b","name":"Campeonato Brasileiro Serie B","type":"League","scope":"Domestic","countryId":"BR","priority":20,"format":{"kind":"LeagueTable","legs":2},"participants":{"explicit":b},"seasonStartMonth":3,"seasonStartDay":20},
{"schema":"competition","id":"br-serie-c","name":"Campeonato Brasileiro Serie C","type":"League","scope":"Domestic","countryId":"BR","priority":30,"format":{"kind":"LeagueTable","legs":1},"participants":{"explicit":c},"seasonStartMonth":4,"seasonStartDay":5},
{"schema":"competition","id":"br-copa-do-brasil","name":"Copa do Brasil","type":"Cup","scope":"Domestic","countryId":"BR","priority":100,"format":{"kind":"Knockout"},"participants":{"selector":{"kind":"allInCountry","country":"BR"}},"seasonStartMonth":2,"seasonStartDay":18},
{"schema":"competition","id":"br-supercopa","name":"Supercopa do Brasil","type":"Cup","scope":"Domestic","countryId":"BR","priority":110,"format":{"kind":"Knockout"},"participants":{"explicit":["flamengo","corinthians"]},"seasonStartMonth":2,"seasonStartDay":1}
]

(root/"package.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
(root/"teams"/"teams.json").write_text(json.dumps({"schema":"team","items":teams},ensure_ascii=False,indent=2),encoding="utf-8")
(root/"players"/"players.json").write_text(json.dumps({"schema":"player","items":real_serie_a_players},ensure_ascii=False,indent=2),encoding="utf-8")
for comp in comps:
    (root/"competitions"/f"{comp['id']}.json").write_text(json.dumps(comp,ensure_ascii=False,indent=2),encoding="utf-8")
print(root)
