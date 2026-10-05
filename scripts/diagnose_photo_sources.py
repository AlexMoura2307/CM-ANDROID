from __future__ import annotations
import json, urllib.request, urllib.parse, time

TM="https://transfermarkt-api.fly.dev"
SOFA="https://www.sofascore.com/api/v1"
FOTMOB_SEARCH="https://apigw.fotmob.com/searchapi/suggest"
HEAD={"User-Agent":"Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/140 Safari/537.36","Accept":"application/json,text/plain,*/*","Referer":"https://www.sofascore.com/"}
IDS=["1208814","962409","844291","1497709","1466510"]

def get(url):
    req=urllib.request.Request(url,headers=HEAD)
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            body=r.read()
            print("HTTP",r.status,url,"bytes",len(body))
            return json.loads(body.decode("utf-8"))
    except Exception as e:
        print("ERR",url,repr(e))
        return {}

for pid in IDS:
    print("\n=== TM",pid,"===")
    p=get(f"{TM}/players/{pid}/profile")
    print(json.dumps({
        "id":p.get("id"),"name":p.get("name"),"fullName":p.get("fullName"),
        "imageUrl":p.get("imageUrl"),"dateOfBirth":p.get("dateOfBirth"),
        "club":p.get("club"),"position":p.get("position")
    },ensure_ascii=False))
    name=p.get("name") or p.get("fullName")
    if not name:
        continue
    q=urllib.parse.quote(str(name))
    for url in [
        f"{SOFA}/search/players/{q}",
        f"{SOFA}/search/all/?q={q}&page=0",
        f"{SOFA}/search/player-team-persons/?q={q}&page=0",
    ]:
        data=get(url)
        print("keys",list(data)[:10])
        vals=data.get("players") or data.get("results") or []
        print("sample",json.dumps(vals[:2],ensure_ascii=False)[:3000])
        time.sleep(0.5)

    fm_url = FOTMOB_SEARCH + "?term=" + q + "&lang=en"
    fm = get(fm_url)
    print("FOTMOB type", type(fm).__name__)
    if isinstance(fm, list):
        print("FOTMOB sample", json.dumps(fm[:5], ensure_ascii=False)[:5000])
    else:
        print("FOTMOB sample", json.dumps(fm, ensure_ascii=False)[:5000])

    groups = fm.get("squadMemberSuggest", []) if isinstance(fm, dict) else []
    if groups and groups[0].get("options"):
        opt = groups[0]["options"][0]
        fid = (opt.get("payload") or {}).get("id")
        if fid:
            pdata = get(f"https://www.fotmob.com/api/data/playerData?id={fid}")
            print("FOTMOB playerData", json.dumps({
                "id": fid,
                "name": pdata.get("name"),
                "birthDate": pdata.get("birthDate"),
                "primaryTeam": pdata.get("primaryTeam"),
                "positionDescription": pdata.get("positionDescription"),
                "marketValues": pdata.get("marketValues"),
            }, ensure_ascii=False)[:5000])
