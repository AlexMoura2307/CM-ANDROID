from __future__ import annotations
import json, urllib.request, urllib.parse, time

TM="https://transfermarkt-api.fly.dev"
SOFA="https://www.sofascore.com/api/v1"
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
        # print only first result/player shape
        vals=data.get("players") or data.get("results") or []
        print("sample",json.dumps(vals[:2],ensure_ascii=False)[:3000])
        time.sleep(0.5)
