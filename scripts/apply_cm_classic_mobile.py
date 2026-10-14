"""Apply a reversible mobile touch/viewport baseline to the CM upstream app."""
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("upstream")
index = root / "index.html"
if not index.is_file():
    raise SystemExit(f"Arquivo não encontrado: {index}")
source = index.read_text(encoding="utf-8")
marker = 'id="cm-classic-mobile"'
style = """<style id="cm-classic-mobile">
@media (max-width: 640px) {
  html, body, #root { width: 100%; max-width: 100%; min-width: 0; }
  body { overflow-x: hidden; -webkit-text-size-adjust: 100%; }
  button, select, input[type="checkbox"], input[type="radio"] { touch-action: manipulation; }
  button, select { min-height: 40px; }
  input[type="checkbox"], input[type="radio"] { min-width: 16px; min-height: 16px; }
  table { max-width: 100%; }
}
</style>"""
if marker in source:
    print("Já aplicado; nenhuma alteração.")
elif "</head>" not in source:
    raise SystemExit("HTML inválido: </head> não encontrado")
else:
    index.write_text(source.replace("</head>", style + "\n</head>", 1), encoding="utf-8")
    print("Base de interface CM Clássico Mobile aplicada.")

# Compact player profile: show attributes first and hide detailed history until requested.
profile = root / "src/components/playerProfile/PlayerProfile.tsx"
if not profile.is_file():
    raise SystemExit(f"Player profile missing: {profile}")
body = profile.read_text(encoding="utf-8")
if "cm-classic-history-toggle" not in body:
    changes = [
        ('import { getContractRiskLevel, getPlayerOvr } from "../../lib/helpers";',
         'import { useState } from "react";\\nimport { getContractRiskLevel, getPlayerOvr } from "../../lib/helpers";'),
        ('  const { t, i18n } = useTranslation();',
         '  const { t, i18n } = useTranslation();\n  const [historyVisible, setHistoryVisible] = useState(false);'),
        ('<div className="grid grid-cols-1 lg:grid-cols-3 gap-5">',
         '<div className="flex flex-col gap-3">'),
        ('        <PlayerProfileContractCard',
         '        <div className="order-2"><PlayerProfileContractCard'),
        ('        <PlayerProfileAttributesCard',
         '        <div className="order-1"><PlayerProfileAttributesCard'),
        ('          radarLabel={t("common.radarView")}\n        />',
         '          radarLabel={t("common.radarView")}\n        /></div>'),
        ('          t={t}\n        />\n\n        {contractActionError',
         '          t={t}\n        /></div>\n\n        {contractActionError'),
        ('      {/* Full-width data cards, stacked for a uniform page */}',
         '''      <button type="button" className="cm-classic-history-toggle mt-3 w-full rounded border px-3 py-2 text-sm" aria-expanded={historyVisible} onClick={() => setHistoryVisible(!historyVisible)}>
        {historyVisible ? "Ocultar histórico" : "Histórico"}
      </button>
      {historyVisible && ('''),
        ('        <PlayerProfileRecentMatchesCard matches={recentMatches} t={t} />\n      </div>',
         '        <PlayerProfileRecentMatchesCard matches={recentMatches} t={t} />\n      </div>)}'),
    ]
    for old, new in changes:
        count = body.count(old)
        if count != 1:
            raise SystemExit(f"Profile patch mismatch ({count}): {old[:65]}")
        body = body.replace(old, new, 1)
    profile.write_text(body, encoding="utf-8")
    print("CM classic profile: attributes first, history collapsed.")
