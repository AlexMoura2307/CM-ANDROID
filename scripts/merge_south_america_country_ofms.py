#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from hashlib import sha256
from pathlib import Path

INPUT = Path(sys.argv[1] if len(sys.argv) > 1 else "country-artifacts")
ROOT = Path("wfe-south-america-merged")
QA_ROOT = Path("wfe-south-america-merged-qa")

EXPECTED_COUNTRIES = {"AR","BO","BR","CL","CO","EC","PY","PE","UY","VE"}

if ROOT.exists():
    shutil.rmtree(ROOT)
if QA_ROOT.exists():
    shutil.rmtree(QA_ROOT)
(ROOT / "teams").mkdir(parents=True)
(ROOT / "players").mkdir(parents=True)
(ROOT / "competitions").mkdir(parents=True)
QA_ROOT.mkdir(parents=True)

ofm_files = sorted(INPUT.rglob("*.ofm"))
if len(ofm_files) != 10:
    raise SystemExit(f"Expected 10 country OFM files, found {len(ofm_files)}: {ofm_files}")

teams_by_id = {}
players_by_id = {}
competitions = {}
asset_hashes = {}
countries = set()
source_packages = []

for ofm in ofm_files:
    with zipfile.ZipFile(ofm) as z:
        pkg = json.loads(z.read("package.json"))
        source_packages.append(pkg["id"])

        team_doc = json.loads(z.read("teams/teams.json"))
        player_doc = json.loads(z.read("players/players.json"))

        for team in team_doc.get("items", []):
            tid = team["id"]
            if tid in teams_by_id and teams_by_id[tid] != team:
                raise SystemExit(f"Conflicting duplicate team id: {tid}")
            teams_by_id[tid] = team
            if team.get("country"):
                countries.add(team["country"])

        for player in player_doc.get("items", []):
            pid = player["id"]
            if pid in players_by_id and players_by_id[pid] != player:
                raise SystemExit(f"Conflicting duplicate player id: {pid}")
            players_by_id[pid] = player

        for name in z.namelist():
            if name.startswith("competitions/") and name.endswith(".json"):
                comp = json.loads(z.read(name))
                cid = comp["id"]
                if cid in competitions and competitions[cid] != comp:
                    raise SystemExit(f"Conflicting duplicate competition id: {cid}")
                competitions[cid] = comp
                if comp.get("countryId"):
                    countries.add(comp["countryId"])

            if not name.startswith("assets/") or name.endswith("/"):
                continue
            data = z.read(name)
            digest = sha256(data).hexdigest()
            if name in asset_hashes:
                if asset_hashes[name] != digest:
                    raise SystemExit(f"Asset path collision with different bytes: {name}")
                continue
            asset_hashes[name] = digest
            target = ROOT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

teams = list(teams_by_id.values())
players = list(players_by_id.values())
team_ids = set(teams_by_id)
player_ids = set(players_by_id)

if countries != EXPECTED_COUNTRIES:
    raise SystemExit(f"Country coverage mismatch. got={sorted(countries)} expected={sorted(EXPECTED_COUNTRIES)}")
if len(teams) < 350:
    raise SystemExit(f"Too few merged teams: {len(teams)}")
if len(players) < 5000:
    raise SystemExit(f"Too few merged players: {len(players)}")

bad_clubs = [p["id"] for p in players if p.get("club") not in team_ids]
if bad_clubs:
    raise SystemExit(f"Players reference missing clubs: {bad_clubs[:20]}")

overage_youth = []
for player in players:
    if not player.get("youth"):
        continue
    age = player.get("age")
    try:
        age = int(age) if age is not None else None
    except Exception:
        age = None
    if age is not None and age > 20:
        overage_youth.append((player["id"], age))
if overage_youth:
    raise SystemExit(f"Youth players over age 20: {overage_youth[:20]}")

bad_participants = []
for comp in competitions.values():
    for tid in comp.get("participants", {}).get("explicit", []):
        if tid not in team_ids:
            bad_participants.append((comp["id"], tid))
if bad_participants:
    raise SystemExit(f"Competition participants missing teams: {bad_participants[:20]}")

missing_photos = []
missing_logos = []
for player in players:
    photo = player.get("photo")
    if photo and not (ROOT / photo).exists():
        missing_photos.append(player["id"])
for team in teams:
    logo = team.get("logo")
    if logo and not (ROOT / logo).exists():
        missing_logos.append(team["id"])
if missing_photos or missing_logos:
    raise SystemExit(
        f"Missing merged assets: photos={missing_photos[:10]} logos={missing_logos[:10]}"
    )

first_division_competitions = [
    c["id"] for c in competitions.values() if int(c.get("priority", 999)) == 10
]

manifest = {
    "schema": "world",
    "id": "cm-south-america-2026",
    "name": "CM America do Sul 2026",
    "description": (
        "Base sul-americana consolidada a partir dos dez lotes nacionais aprovados, "
        "com clubes, elenco principal, reservas, base, fotos reais disponíveis, "
        "logos, posições e dados biográficos; atributos calculados pelo modelo CM."
    ),
    "version": "1.0.0",
    "author": "CM",
    "license": "CC0-1.0",
    "packageType": "database",
    "gameMinVersion": "0.3.0",
    "formatVersion": 1,
    "baseYear": 2026,
    "defaultActiveRegions": [],
    "defaultActiveCompetitions": sorted(first_division_competitions),
}

(ROOT / "package.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
)
(ROOT / "teams" / "teams.json").write_text(
    json.dumps({"schema":"team","items":teams}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
(ROOT / "players" / "players.json").write_text(
    json.dumps({"schema":"player","items":players}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
for cid, comp in sorted(competitions.items()):
    (ROOT / "competitions" / f"{cid}.json").write_text(
        json.dumps(comp, ensure_ascii=False, indent=2), encoding="utf-8"
    )

qa = {
    "sourcePackages": sorted(source_packages),
    "countries": sorted(countries),
    "clubsTotal": len(teams),
    "playersTotal": len(players),
    "competitionsTotal": len(competitions),
    "playersWithPhotos": sum(1 for p in players if p.get("photo")),
    "clubsWithLogos": sum(1 for t in teams if t.get("logo")),
    "youthPlayersTotal": sum(1 for p in players if p.get("youth")),
    "assetsTotal": len(asset_hashes),
    "duplicateTeamIds": 0,
    "duplicatePlayerIds": 0,
    "badPlayerClubRefs": 0,
    "overageYouth": 0,
    "badCompetitionParticipants": 0,
    "missingPhotoAssets": 0,
    "missingLogoAssets": 0,
}
qa["photoCoverage"] = round(qa["playersWithPhotos"]/max(1,qa["playersTotal"]),4)
qa["logoCoverage"] = round(qa["clubsWithLogos"]/max(1,qa["clubsTotal"]),4)

(QA_ROOT / "summary.json").write_text(
    json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(qa, ensure_ascii=False, indent=2))
print(ROOT)
