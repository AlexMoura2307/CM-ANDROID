from pathlib import Path
import json

root = Path("upstream")

# Final CM mobile identity for the South America integrated test build.
conf_path = root / "src-tauri" / "tauri.conf.json"
conf = json.loads(conf_path.read_text(encoding="utf-8"))
conf["productName"] = "CM Teste 4"
conf["identifier"] = "com.cm.clubemanager.test4"
conf.setdefault("app", {}).setdefault("windows", [{}])[0]["title"] = "CM Teste 4"

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
