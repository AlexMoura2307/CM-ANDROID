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
