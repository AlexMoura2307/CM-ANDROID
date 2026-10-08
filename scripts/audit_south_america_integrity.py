#!/usr/bin/env python3
import argparse, json, re, sys, zipfile
from collections import Counter
from pathlib import Path

GENERIC_PLAYER_RE = re.compile(r"^Jogador\s+\S+", re.I)

def read_json_from_ofm(path: Path, suffix: str):
    if not zipfile.is_zipfile(path):
        raise RuntimeError(f"{path} nao e um arquivo OFM/ZIP valido")
    with zipfile.ZipFile(path) as z:
        matches = [n for n in z.namelist() if n.endswith(suffix)]
        if len(matches) != 1:
            raise RuntimeError(f"Esperado 1 arquivo *{suffix}, encontrados {len(matches)}: {matches[:5]}")
        return json.loads(z.read(matches[0]).decode("utf-8"))

def read_competitions(path: Path):
    items = []
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if "/competitions/" in n and n.endswith(".json")]
        if not names:
            names = [n for n in z.namelist() if n.startswith("competitions/") and n.endswith(".json")]
        for name in names:
            obj = json.loads(z.read(name).decode("utf-8"))
            items.append((name, obj))
    return items

def duplicates(values):
    c = Counter(values)
    return sorted([k for k,v in c.items() if v > 1])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ofm")
    ap.add_argument("--report", default="cm-integrity-audit.json")
    args = ap.parse_args()
    path = Path(args.ofm)

    teams_doc = read_json_from_ofm(path, "teams/teams.json")
    players_doc = read_json_from_ofm(path, "players/players.json")
    competition_files = read_competitions(path)

    teams = teams_doc.get("items", [])
    players = players_doc.get("items", [])
    competitions = [obj for _, obj in competition_files]

    team_ids = [str(x.get("id") or "").strip() for x in teams]
    player_ids = [str(x.get("id") or "").strip() for x in players]
    competition_ids = [str(x.get("id") or "").strip() for x in competitions]

    errors = []
    warnings = []

    def require_no_empty(label, values):
        idx = [i for i,v in enumerate(values) if not v]
        if idx:
            errors.append({"check": f"{label}.emptyIds", "count": len(idx), "sample": idx[:20]})

    require_no_empty("players", player_ids)
    require_no_empty("teams", team_ids)
    require_no_empty("competitions", competition_ids)

    for label, values in (("players", player_ids), ("teams", team_ids), ("competitions", competition_ids)):
        dup = duplicates(values)
        if dup:
            errors.append({"check": f"{label}.duplicateIds", "count": len(dup), "sample": dup[:20]})

    global_ids = [("player", v) for v in player_ids if v] + [("team", v) for v in team_ids if v] + [("competition", v) for v in competition_ids if v]
    by_id = {}
    collisions = []
    for kind, value in global_ids:
        prev = by_id.get(value)
        if prev and prev != kind:
            collisions.append((value, prev, kind))
        else:
            by_id[value] = kind
    if collisions:
        errors.append({"check":"global.crossEntityIdCollision","count":len(collisions),"sample":collisions[:20]})

    team_set = set(team_ids)
    comp_set = set(competition_ids)

    bad_player_refs = []
    generic_names = []
    blank_names = []
    bad_attr = []
    for p in players:
        pid = str(p.get("id") or "")
        name = str(p.get("name") or "").strip()
        club = str(p.get("club") or "").strip()
        if not name:
            blank_names.append(pid)
        elif GENERIC_PLAYER_RE.match(name):
            generic_names.append({"id":pid,"name":name,"club":club})
        if club not in team_set:
            bad_player_refs.append({"id":pid,"club":club})
        attrs = p.get("attributes")
        if not isinstance(attrs, dict) or not attrs:
            bad_attr.append(pid)
    if blank_names:
        errors.append({"check":"players.blankNames","count":len(blank_names),"sample":blank_names[:30]})
    if generic_names:
        errors.append({"check":"players.genericNames","count":len(generic_names),"sample":generic_names[:30]})
    if bad_player_refs:
        errors.append({"check":"players.invalidClubRefs","count":len(bad_player_refs),"sample":bad_player_refs[:30]})
    if bad_attr:
        errors.append({"check":"players.missingAttributes","count":len(bad_attr),"sample":bad_attr[:30]})

    team_blank_names = [x.get("id") for x in teams if not str(x.get("name") or "").strip()]
    if team_blank_names:
        errors.append({"check":"teams.blankNames","count":len(team_blank_names),"sample":team_blank_names[:30]})

    duplicate_team_names = []
    team_name_keys = Counter((str(x.get("country") or "").strip(), str(x.get("name") or "").strip().casefold()) for x in teams)
    for (country,name), count in team_name_keys.items():
        if name and count > 1:
            duplicate_team_names.append({"country":country,"name":name,"count":count})
    if duplicate_team_names:
        warnings.append({"check":"teams.duplicateNamesWithinCountry","count":len(duplicate_team_names),"sample":duplicate_team_names[:30]})

    bad_comp_refs = []
    duplicate_participants = []
    file_id_mismatch = []
    blank_comp_names = []
    for filename, c in competition_files:
        cid = str(c.get("id") or "").strip()
        if not str(c.get("name") or "").strip():
            blank_comp_names.append(cid)
        participants = c.get("participants", {}).get("explicit", [])
        participant_ids = [str(x).strip() for x in participants]
        dup = duplicates(participant_ids)
        if dup:
            duplicate_participants.append({"competition":cid,"duplicates":dup[:20]})
        missing = [x for x in participant_ids if x not in team_set]
        if missing:
            bad_comp_refs.append({"competition":cid,"missing":missing[:30]})
        expected = Path(filename).stem
        if cid and expected != cid:
            file_id_mismatch.append({"file":filename,"id":cid})
    if blank_comp_names:
        errors.append({"check":"competitions.blankNames","count":len(blank_comp_names),"sample":blank_comp_names[:30]})
    if duplicate_participants:
        errors.append({"check":"competitions.duplicateParticipantIds","count":len(duplicate_participants),"sample":duplicate_participants[:20]})
    if bad_comp_refs:
        errors.append({"check":"competitions.invalidTeamRefs","count":len(bad_comp_refs),"sample":bad_comp_refs[:20]})
    if file_id_mismatch:
        errors.append({"check":"competitions.filenameIdMismatch","count":len(file_id_mismatch),"sample":file_id_mismatch[:20]})

    report = {
        "status": "PASS" if not errors else "FAIL",
        "totals": {
            "players": len(players),
            "teams": len(teams),
            "competitions": len(competitions),
            "uniquePlayerIds": len(set(player_ids)),
            "uniqueTeamIds": len(set(team_ids)),
            "uniqueCompetitionIds": len(set(competition_ids)),
        },
        "checks": {
            "playerIdsUnique": len(set(player_ids)) == len(player_ids) and all(player_ids),
            "teamIdsUnique": len(set(team_ids)) == len(team_ids) and all(team_ids),
            "competitionIdsUnique": len(set(competition_ids)) == len(competition_ids) and all(competition_ids),
            "crossEntityIdsUnique": not collisions,
            "playerClubReferencesValid": not bad_player_refs,
            "competitionTeamReferencesValid": not bad_comp_refs,
            "playerNamesValid": not blank_names and not generic_names,
            "playerAttributesPresent": not bad_attr,
        },
        "errors": errors,
        "warnings": warnings,
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())
