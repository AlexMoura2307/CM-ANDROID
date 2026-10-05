from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode
import json
import time
import unicodedata
import urllib.request

TM_BASE = "https://transfermarkt-api.fly.dev"
OUT = Path("south-america-club-catalog")

COUNTRIES = {
    "AR": ("Argentina",),
    "BO": ("Bolivia",),
    "BR": ("Brazil", "Brasil"),
    "CL": ("Chile",),
    "CO": ("Colombia",),
    "EC": ("Ecuador",),
    "PY": ("Paraguay",),
    "PE": ("Peru", "Perú"),
    "UY": ("Uruguay",),
    "VE": ("Venezuela",),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/140 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}

_last_request = 0.0


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.lower().split())


def api_json(path: str) -> dict:
    global _last_request
    wait = 1.60 - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    url = path if path.startswith("http") else TM_BASE + path
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            _last_request = time.monotonic()
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            time.sleep(3 + attempt * 3)
    raise RuntimeError(f"API indisponivel para {url}: {last}")


def main() -> None:
    if OUT.exists():
        for child in OUT.rglob("*"):
            if child.is_file():
                child.unlink()
    OUT.mkdir(parents=True, exist_ok=True)

    countries_payload = api_json("/countries/")
    countries = countries_payload.get("countries", [])
    by_name = {norm(item.get("name")): item for item in countries if item.get("id")}

    consolidated = {}
    all_ids = set()
    duplicate_ids = []

    for code, aliases in COUNTRIES.items():
        source_country = None
        for alias in aliases:
            source_country = by_name.get(norm(alias))
            if source_country:
                break
        if not source_country:
            raise RuntimeError(f"Pais nao encontrado na fonte: {code} {aliases}")

        country_id = source_country["id"]
        payload = api_json("/clubs/?" + urlencode({"country_id": country_id}))
        clubs = [
            {"id": str(item["id"]), "name": item.get("name") or f"Club {item['id']}"}
            for item in payload.get("clubs", [])
            if item.get("id")
        ]
        clubs.sort(key=lambda item: norm(item["name"]))

        if not clubs:
            raise RuntimeError(f"Nenhum clube retornado para {code}")

        country_seen = set()
        cleaned = []
        for club in clubs:
            if club["id"] in country_seen:
                continue
            country_seen.add(club["id"])
            if club["id"] in all_ids:
                duplicate_ids.append((code, club["id"], club["name"]))
                continue
            all_ids.add(club["id"])
            cleaned.append(club)

        record = {
            "countryCode": code,
            "countryName": aliases[0],
            "sourceCountryId": country_id,
            "clubs": cleaned,
            "clubCount": len(cleaned),
        }
        consolidated[code] = record
        (OUT / f"{code}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"{code}: {len(cleaned)} clubes catalogados")

    total = sum(item["clubCount"] for item in consolidated.values())
    qa = {
        "countries": len(consolidated),
        "clubsTotal": total,
        "duplicateSourceIdsSkipped": duplicate_ids,
        "countryCounts": {code: data["clubCount"] for code, data in consolidated.items()},
        "sourceNote": (
            "Catalogo retornado pelo endpoint de clubes por pais da fonte. "
            "Competições e divisões adicionais podem complementar clubes ausentes."
        ),
    }

    if len(consolidated) != 10:
        raise RuntimeError(f"QA: esperado 10 paises, obtido {len(consolidated)}")
    if total < 100:
        raise RuntimeError(f"QA: catalogo muito pequeno: {total} clubes")

    (OUT / "all-clubs.json").write_text(
        json.dumps({"countries": consolidated, "qa": qa}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(qa, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
