from pathlib import Path
import json

root = Path("upstream")

# Final CM mobile identity for the South America integrated test build.
conf_path = root / "src-tauri" / "tauri.conf.json"
conf = json.loads(conf_path.read_text(encoding="utf-8"))
conf["productName"] = "CM Teste 5"
conf["identifier"] = "com.cm.clubemanager.test5"
conf.setdefault("app", {}).setdefault("windows", [{}])[0]["title"] = "CM Teste 5"

resources = conf.setdefault("bundle", {}).setdefault("resources", {})
resources.pop("resources/wfe-brasil-2026-fase1.ofm", None)
resources["resources/cm-south-america-2026.ofm"] = "packages/cm-south-america-2026.ofm"
conf_path.write_text(json.dumps(conf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# prepare_cm.py currently injects the bundled-package loader using the former
# Brazil resource name. Retarget the injected loader to the consolidated
# South America package without changing gameplay logic.
world_path = root / "src-tauri" / "src" / "commands" / "world.rs"
src = world_path.read_text(encoding="utf-8")
src = src.replace("WFE_BRASIL_PACKAGE_BYTES", "CM_SOUTH_AMERICA_PACKAGE_BYTES")
src = src.replace("wfe-brasil-2026-fase1.ofm", "cm-south-america-2026.ofm")
world_path.write_text(src, encoding="utf-8")

print("CM Teste 4 configured for consolidated South America package")


# Final CM branding. The base customization script still contains legacy WFE
# labels; the CM integration pass removes those from the shipped Teste 4 UI.
cm_logo = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 360" role="img" aria-label="CM">
  <rect width="1200" height="360" rx="46" fill="#101a33"/>
  <circle cx="190" cy="180" r="118" fill="#ffffff"/>
  <text x="190" y="222" text-anchor="middle" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="130" fill="#101a33">CM</text>
  <text x="362" y="205" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="146" fill="#ffffff">CM</text>
  <text x="370" y="275" font-family="Arial,Helvetica,sans-serif" font-weight="700" font-size="34" fill="#a9b4ca" letter-spacing="10">CLUBE MANAGER</text>
</svg>
"""
cm_icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <rect width="1024" height="1024" rx="220" fill="#101a33"/>
  <circle cx="512" cy="512" r="330" fill="#ffffff"/>
  <text x="512" y="610" text-anchor="middle" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="300" fill="#101a33">CM</text>
</svg>
"""
(root / "public" / "cm-logo.svg").write_text(cm_logo, encoding="utf-8")
(root / "public" / "cm-app-icon.svg").write_text(cm_icon, encoding="utf-8")

replacements = {
    root / "src" / "App.tsx": [
        ("WFE - World Football Empire", "CM - Clube Manager"),
    ],
    root / "src" / "main.tsx": [
        ("WFE - World Football Empire", "CM - Clube Manager"),
    ],
    root / "index.html": [
        ("WFE - World Football Empire", "CM - Clube Manager"),
        ('href="/wfe-app-icon.svg"', 'href="/cm-app-icon.svg"'),
    ],
    root / "src" / "pages" / "MainMenu.tsx": [
        ('src="/wfe-logo.svg"', 'src="/cm-logo.svg"'),
    ],
    root / "src" / "components" / "dashboard" / "DashboardSidebar.tsx": [
        ('src="/wfe-app-icon.svg"', 'src="/cm-app-icon.svg"'),
    ],
}
for file_path, pairs in replacements.items():
    if not file_path.exists():
        continue
    file_src = file_path.read_text(encoding="utf-8")
    for old, new in pairs:
        file_src = file_src.replace(old, new)
    file_path.write_text(file_src, encoding="utf-8")

print("CM branding applied")


package_rs_path = root / "src-tauri" / "crates" / "ofm_core" / "src" / "generator" / "package.rs"
package_rs = package_rs_path.read_text(encoding="utf-8")
if "pub const MAX_FILE_COUNT: usize = 10_000;" not in package_rs:
    raise RuntimeError("MAX_FILE_COUNT upstream marker not found")
package_rs = package_rs.replace(
    "pub const MAX_FILE_COUNT: usize = 10_000;",
    "pub const MAX_FILE_COUNT: usize = 25_000;",
    1,
)
package_rs_path.write_text(package_rs, encoding="utf-8")
print("CM South America archive file-count limit set to 25,000")
