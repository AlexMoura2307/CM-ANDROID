from pathlib import Path
from datetime import datetime, timezone
import json, shutil, time, unicodedata, urllib.request

root = Path("wfe-brasil-fase1")
if root.exists():
    shutil.rmtree(root)
(root/"teams").mkdir(parents=True)
(root/"competitions").mkdir(parents=True)
(root/"players").mkdir(parents=True)

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
# Fonte operacional: endpoint publico do SofaScore. Os IDs dos jogadores sao
# preservados no WFE para evitar duplicacao quando um atleta trocar de clube.
SOFASCORE_SEASON_ID = 87678
SOFASCORE_TOURNAMENT_ID = 325
SOFASCORE_BASES = [
    "https://www.sofascore.com/api/v1",
    "https://api.sofascore.com/api/v1",
]

def _http_json(path):
    last_error = None
    for attempt in range(4):
        for base in SOFASCORE_BASES:
            try:
                request = urllib.request.Request(
                    base + path,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/140 Safari/537.36",
                        "Accept": "application/json,text/plain,*/*",
                    },
                )
                with urllib.request.urlopen(request, timeout=25) as response:
                    return json.loads(response.read().decode("utf-8"))
            except Exception as exc:
                last_error = exc
        time.sleep(2 + attempt * 2)
    raise RuntimeError(f"SofaScore indisponivel para {path}: {last_error}")

def _norm(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(
        "".join(ch if ch.isalnum() else " " for ch in value.lower()).split()
    )

SOFA_ALIASES = {
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
    "flamengo": 81,
    "palmeiras": 81,
    "athletico-pr": 76,
    "fluminense": 77,
    "bahia": 77,
    "cruzeiro": 76,
    "atletico-mg": 76,
    "santos": 74,
    "red-bull-bragantino": 74,
    "sao-paulo": 75,
    "botafogo-rj": 74,
    "corinthians": 74,
    "internacional": 74,
    "gremio": 73,
    "vasco": 73,
    "mirassol": 71,
    "coritiba": 71,
    "vitoria": 71,
    "chapecoense": 69,
    "remo": 69,
}

def _birth_date(player):
    raw = player.get("dateOfBirth")
    if isinstance(raw, str) and len(raw) >= 10:
        return raw[:10]
    ts = player.get("dateOfBirthTimestamp")
    if isinstance(ts, (int, float)) and ts > 0:
        return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
    return None

def _age_from_birth(value):
    if not value:
        return 25
    try:
        born = datetime.strptime(value, "%Y-%m-%d").date()
        return max(15, 2026 - born.year)
    except Exception:
        return 25

def _position(player):
    raw = str(
        player.get("specificPosition")
        or player.get("position")
        or player.get("positionCode")
        or ""
    ).strip().upper().replace("-", "").replace("_", "")
    exact = {
        "G": "Goalkeeper", "GK": "Goalkeeper", "GOALKEEPER": "Goalkeeper",
        "DC": "CenterBack", "CB": "CenterBack", "CENTREBACK": "CenterBack", "CENTERBACK": "CenterBack",
        "DL": "LeftBack", "LB": "LeftBack", "LEFTBACK": "LeftBack",
        "DR": "RightBack", "RB": "RightBack", "RIGHTBACK": "RightBack",
        "DM": "DefensiveMidfielder", "DMC": "DefensiveMidfielder",
        "MC": "CentralMidfielder", "CM": "CentralMidfielder", "CENTRALMIDFIELDER": "CentralMidfielder",
        "ML": "LeftMidfielder", "LM": "LeftMidfielder",
        "MR": "RightMidfielder", "RM": "RightMidfielder",
        "AM": "AttackingMidfielder", "AMC": "AttackingMidfielder",
        "AML": "LeftWinger", "LW": "LeftWinger",
        "AMR": "RightWinger", "RW": "RightWinger",
        "ST": "Striker", "CF": "Striker", "STRIKER": "Striker",
        "D": "Defender", "DEFENDER": "Defender",
        "M": "Midfielder", "MIDFIELDER": "Midfielder",
        "F": "Forward", "FW": "Forward", "FORWARD": "Forward",
    }
    return exact.get(raw, "Midfielder")

def _foot(player):
    value = str(player.get("preferredFoot") or player.get("foot") or "Right").lower()
    if "left" in value:
        return "Left"
    if "both" in value:
        return "Both"
    return "Right"

def _names(player):
    name = (player.get("name") or player.get("shortName") or "Jogador").strip()
    first = (player.get("firstName") or "").strip()
    last = (player.get("lastName") or "").strip()
    if not first:
        bits = name.split()
        first = bits[0] if bits else name
    if not last:
        bits = name.split()
        last = " ".join(bits[1:]) if len(bits) > 1 else first
    return name, first, last

def _rating(team_id, sofa_player_id, age):
    base = TEAM_OVR_BASE.get(team_id, 72)
    jitter = ((int(sofa_player_id) * 37) % 9) - 4
    age_adj = -3 if age <= 19 else (-1 if age >= 34 else 0)
    return max(58, min(85, base + jitter + age_adj))

def _potential(overall, age, sofa_player_id):
    if age <= 18:
        bonus = 8 + (int(sofa_player_id) % 5)
    elif age <= 21:
        bonus = 5 + (int(sofa_player_id) % 4)
    elif age <= 24:
        bonus = 2 + (int(sofa_player_id) % 3)
    else:
        bonus = 0
    return max(overall, min(92, overall + bonus))

def fetch_real_serie_a_players():
    standings = _http_json(
        f"/unique-tournament/{SOFASCORE_TOURNAMENT_ID}/season/{SOFASCORE_SEASON_ID}/standings/total"
    )
    sofa_teams = {}
    for table in standings.get("standings", []):
        for row in table.get("rows", []):
            item = row.get("team") or {}
            if item.get("id") and item.get("name"):
                sofa_teams[_norm(item["name"])] = item

    results = []
    counts = {}
    missing = []
    for team_id, *_ in A:
        found = None
        aliases = [_norm(x) for x in SOFA_ALIASES.get(team_id, [])]
        for alias in aliases:
            if alias in sofa_teams:
                found = sofa_teams[alias]
                break
        if found is None:
            # ultima tentativa por inclusao para pequenas variacoes de nome
            for key, item in sofa_teams.items():
                if any(alias in key or key in alias for alias in aliases if len(alias) >= 5):
                    found = item
                    break
        if found is None:
            missing.append(team_id)
            continue

        payload = _http_json(f"/team/{found['id']}/players")
        seen = set()
        for entry in payload.get("players", []):
            player = entry.get("player") or {}
            sofa_id = player.get("id")
            name = player.get("name")
            if not sofa_id or not name or sofa_id in seen:
                continue
            seen.add(sofa_id)

            birth = _birth_date(player)
            age = _age_from_birth(birth)
            display_name, first, last = _names(player)
            overall = _rating(team_id, sofa_id, age)
            nationality = (
                (player.get("country") or {}).get("alpha2")
                or (player.get("country") or {}).get("alpha3")
                or "BR"
            ).upper()

            item = {
                "id": f"sofa-{sofa_id}",
                "name": display_name,
                "firstName": first,
                "lastName": last,
                "club": team_id,
                "nationality": nationality,
                "position": _position(player),
                "footedness": _foot(player),
                "overall": overall,
                "potential": _potential(overall, age, sofa_id),
                # Elenco profissional real. A Base real sera cadastrada separadamente;
                # nao classificamos todo sub-20 automaticamente como jogador da Base.
                "youth": False,
            }
            if birth:
                item["dateOfBirth"] = birth
            else:
                item["age"] = age
            results.append(item)

        counts[team_id] = len(seen)
        time.sleep(0.15)

    if missing:
        raise RuntimeError("Times da Serie A nao encontrados no SofaScore: " + ", ".join(missing))
    too_small = {team_id: count for team_id, count in counts.items() if count < 15}
    if too_small:
        raise RuntimeError(f"Elencos reais incompletos no SofaScore: {too_small}")
    if len(results) < 360:
        raise RuntimeError(f"Poucos jogadores reais coletados para Serie A: {len(results)}")

    print("WFE Brasil: jogadores reais Serie A =", len(results))
    print("WFE Brasil: atletas por clube =", counts)
    return results

real_serie_a_players = fetch_real_serie_a_players()

manifest={
 "schema":"world","id":"wfe-brasil-2026-fase1","name":"WFE Brasil 2026 - Fase 1",
 "description":"Base WFE Brasil com Series A, B e C, copas nacionais e elencos reais da Serie A 2026.",
 "version":"0.2.0","author":"WFE","license":"CC0-1.0","packageType":"database",
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
