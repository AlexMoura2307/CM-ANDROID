from pathlib import Path
import json, shutil

root = Path("cm-brasil-fase1")
if root.exists():
    shutil.rmtree(root)
(root/"teams").mkdir(parents=True)
(root/"competitions").mkdir(parents=True)

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

manifest={
 "schema":"world","id":"cm-brasil-2026-fase1","name":"CM Brasil 2026 - Fase 1",
 "description":"Base de teste CM Brasil com Series A, B e C e copas nacionais.",
 "version":"0.1.1","author":"CM","license":"CC0-1.0","packageType":"database",
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
for comp in comps:
    (root/"competitions"/f"{comp['id']}.json").write_text(json.dumps(comp,ensure_ascii=False,indent=2),encoding="utf-8")
print(root)
