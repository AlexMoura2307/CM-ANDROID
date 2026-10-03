from pathlib import Path
import json
import re

root = Path("upstream")

# Nome do pacote/scripts Android
pkg_path = root / "package.json"
pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
pkg["name"] = "cm-football-manager"
scripts = pkg.setdefault("scripts", {})
scripts["android:init"] = "tauri android init"
scripts["android:dev"] = "tauri android dev"
scripts["android:build"] = "tauri android build"
pkg_path.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Lockfile: só troca o nome do pacote raiz para manter npm ci coerente
lock_path = root / "package-lock.json"
lock = json.loads(lock_path.read_text(encoding="utf-8"))
lock["name"] = "cm-football-manager"
if "" in lock.get("packages", {}):
    lock["packages"][""]["name"] = "cm-football-manager"
lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Tauri / Android - versão de teste instalada ao lado do CM atual
conf_path = root / "src-tauri" / "tauri.conf.json"
conf = json.loads(conf_path.read_text(encoding="utf-8"))
conf["productName"] = "CM Teste"
conf["identifier"] = "com.cm.footballmanager.test"
resources = conf.setdefault("bundle", {}).setdefault("resources", {})
resources["resources/cm-brasil-2026-fase1.ofm"] = "packages/cm-brasil-2026-fase1.ofm"
conf_path.write_text(json.dumps(conf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Base Brasil embutida: copia o pacote de resources para a pasta interna de pacotes
world_path = root / "src-tauri" / "src" / "commands" / "world.rs"
world_src = world_path.read_text(encoding="utf-8")
if "ensure_bundled_cm_package" not in world_src:
    marker = """fn packages_dir(app_handle: &tauri::AppHandle) -> Result<std::path::PathBuf, String> {
    let app_data_dir = app_handle
        .path()
        .app_data_dir()
        .map_err(|e| e.to_string())?;
    Ok(app_data_dir.join("packages"))
}
"""
    helper = marker + r'''

fn ensure_bundled_cm_package(app_handle: &tauri::AppHandle) -> Result<(), String> {
    let resource_dir = app_handle.path().resource_dir().map_err(|e| e.to_string())?;
    let bundled = resource_dir.join("packages").join("cm-brasil-2026-fase1.ofm");
    if !bundled.exists() {
        return Ok(());
    }

    let dir = packages_dir(app_handle)?;
    std::fs::create_dir_all(&dir)
        .map_err(|_| "be.error.package.installFailed".to_string())?;
    let dest = dir.join("cm-brasil-2026-fase1.ofm");

    let should_copy = match (std::fs::metadata(&bundled), std::fs::metadata(&dest)) {
        (Ok(src), Ok(dst)) => src.len() != dst.len(),
        (Ok(_), Err(_)) => true,
        _ => false,
    };

    if should_copy {
        std::fs::copy(&bundled, &dest)
            .map_err(|_| "be.error.package.installFailed".to_string())?;
    }
    Ok(())
}
'''
    if marker not in world_src:
        raise RuntimeError("packages_dir marker not found")
    world_src = world_src.replace(marker, helper)

    list_marker = """pub fn list_installed_packages(
    app_handle: tauri::AppHandle,
) -> Result<Vec<ofm_core::generator::PackageInfo>, String> {
    info!("[cmd] list_installed_packages");
"""
    list_repl = list_marker + """    ensure_bundled_cm_package(&app_handle)?;
"""
    if list_marker not in world_src:
        raise RuntimeError("list_installed_packages marker not found")
    world_src = world_src.replace(list_marker, list_repl)

world_path.write_text(world_src, encoding="utf-8")

# Português do Brasil como padrão no i18n
i18n_path = root / "src" / "i18n" / "index.ts"
i18n = i18n_path.read_text(encoding="utf-8")
i18n = re.sub(
    r'function detectInitialLanguage\(\): string \{.*?\n\}',
    'function detectInitialLanguage(): string {\n  return "pt-BR";\n}',
    i18n,
    flags=re.S,
)
i18n_path.write_text(i18n, encoding="utf-8")

# Português do Brasil também nos defaults persistidos do frontend e backend.
settings_store_path = root / "src" / "store" / "settingsStore.ts"
settings_store = settings_store_path.read_text(encoding="utf-8")
settings_store = settings_store.replace('  language: "en",', '  language: "pt-BR",', 1)
settings_store_path.write_text(settings_store, encoding="utf-8")

settings_rs_path = root / "src-tauri" / "src" / "commands" / "settings.rs"
settings_rs = settings_rs_path.read_text(encoding="utf-8")
settings_rs = settings_rs.replace(
    'fn default_language() -> String {\n    "en".to_string()\n}',
    'fn default_language() -> String {\n    "pt-BR".to_string()\n}',
)
settings_rs = settings_rs.replace(
    '            language: "en".to_string(),',
    '            language: "pt-BR".to_string(),',
    1,
)
normalize_marker = """fn normalize_loaded_settings(mut settings: AppSettings) -> AppSettings {
    settings.currency = currency::normalize_currency_code(&settings.currency)
"""
normalize_repl = """fn normalize_loaded_settings(mut settings: AppSettings) -> AppSettings {
    if settings.language == "en" {
        settings.language = "pt-BR".to_string();
    }
    settings.currency = currency::normalize_currency_code(&settings.currency)
"""
if normalize_marker in settings_rs:
    settings_rs = settings_rs.replace(normalize_marker, normalize_repl, 1)
settings_rs_path.write_text(settings_rs, encoding="utf-8")

# Nome CM em todos os idiomas
locales_dir = root / "src" / "i18n" / "locales"
for locale_path in locales_dir.glob("*.json"):
    data = json.loads(locale_path.read_text(encoding="utf-8"))
    data.setdefault("app", {})["name"] = "CM"
    locale_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Título da janela
app_path = root / "src" / "App.tsx"
app = app_path.read_text(encoding="utf-8")
app = app.replace(
    'await getCurrentWindow().setTitle(`Openfoot Manager ${formatAppVersion()}`);',
    'await getCurrentWindow().setTitle(`CM Teste ${formatAppVersion()}`);',
)
app_path.write_text(app, encoding="utf-8")

# Logo temporário CM
logo = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 360" role="img" aria-labelledby="title desc">
  <title id="title">CM</title>
  <desc id="desc">CM Football Manager</desc>
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#18c98b"/>
      <stop offset="1" stop-color="#d9dd35"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="360" rx="44" fill="#101a33"/>
  <circle cx="190" cy="180" r="112" fill="url(#g)"/>
  <text x="355" y="216" font-family="Arial Black, Arial, sans-serif" font-weight="900" font-size="160" fill="#fff">CM</text>
  <text x="365" y="286" font-family="Arial, sans-serif" font-weight="700" font-size="38" fill="#9aa7c1" letter-spacing="12">FOOTBALL MANAGER</text>
</svg>
"""
(root / "public" / "cm-logo.svg").write_text(logo, encoding="utf-8")

menu_path = root / "src" / "pages" / "MainMenu.tsx"
menu = menu_path.read_text(encoding="utf-8")
menu = menu.replace('src="/openfootlogo.svg"', 'src="/cm-logo.svg"')
menu = menu.replace(
    'className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-navy-900 transition-colors duration-500 relative overflow-x-hidden"',
    'className="min-h-screen flex items-center justify-center bg-gray-100 px-3 py-6 dark:bg-navy-900 transition-colors duration-500 relative overflow-x-hidden sm:px-4 sm:py-8"',
)
menu = menu.replace(
    'className="bg-white dark:bg-navy-800 p-8 rounded-b-2xl',
    'className="bg-white dark:bg-navy-800 p-5 sm:p-8 rounded-b-2xl',
)
menu_path.write_text(menu, encoding="utf-8")

# CM mobile UI: menu lateral vira drawer acionado por hamburger.
sidebar_path = root / "src" / "components" / "dashboard" / "DashboardSidebar.tsx"
sidebar = sidebar_path.read_text(encoding="utf-8")
sidebar = sidebar.replace(
    'collapsed ? "w-20" : "w-64"',
    'collapsed ? "w-20" : "w-full"',
)
sidebar_path.write_text(sidebar, encoding="utf-8")

dashboard_path = root / "src" / "pages" / "Dashboard.tsx"
dashboard = dashboard_path.read_text(encoding="utf-8")
dashboard = dashboard.replace(
    'import { Cpu, Eye, Gamepad2 } from "lucide-react";',
    'import { Cpu, Eye, Gamepad2, Menu } from "lucide-react";',
)
dashboard = dashboard.replace(
    'const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);',
    'const [isSidebarOpen, setIsSidebarOpen] = useState(false);',
)
dashboard = dashboard.replace(
    """  function handleNavClick(tab: string): void {
    setProfileNavigation((currentState) => navigateDashboardProfiles(currentState, tab));
  }
""",
    """  function handleNavClick(tab: string): void {
    setProfileNavigation((currentState) => navigateDashboardProfiles(currentState, tab));
    setIsSidebarOpen(false);
  }
""",
)
dashboard = dashboard.replace(
    """  function handleNavigateSettings(): void {
    navigate("/settings", { state: { from: "/dashboard" } });
  }
""",
    """  function handleNavigateSettings(): void {
    setIsSidebarOpen(false);
    navigate("/settings", { state: { from: "/dashboard" } });
  }
""",
)
old_sidebar_block = """  return (
    <div className="min-h-screen bg-gray-100 dark:bg-navy-900 flex transition-colors duration-300">
      <DashboardSidebar
        activeTab={profileNavigation.activeTab}
        collapsed={isSidebarCollapsed}
        onNavClick={handleNavClick}
        onToggleCollapse={() => {
          setIsSidebarCollapsed((currentValue) => !currentValue);
        }}
        unreadMessagesCount={unreadMessagesCount}
        todayHasMatch={hasMatchToday}
        managerName={managerName}
        teamName={myTeamName}
        onNavigateSettings={handleNavigateSettings}
        isUnemployed={isUnemployed ?? false}
        onExitClick={() => {
          if (!isExitingToMenu) {
            setShowExitConfirm(true);
          }
        }}
      />
"""
new_sidebar_block = """  return (
    <div className="relative min-h-screen bg-gray-100 transition-colors duration-300 dark:bg-navy-900">
      <button
        type="button"
        onClick={() => setIsSidebarOpen(true)}
        aria-label={t("dashboard.expandSidebar")}
        className="fixed left-3 top-3 z-30 flex h-10 w-10 items-center justify-center rounded-lg bg-navy-800 text-white shadow-lg ring-1 ring-white/10 active:scale-95"
      >
        <Menu className="h-5 w-5" />
      </button>

      {isSidebarOpen ? (
        <>
          <button
            type="button"
            aria-label={t("common.close")}
            onClick={() => setIsSidebarOpen(false)}
            className="fixed inset-0 z-40 bg-black/50"
          />
          <div className="fixed inset-y-0 left-0 z-50 w-72 max-w-[86vw] shadow-2xl">
            <DashboardSidebar
              activeTab={profileNavigation.activeTab}
              collapsed={false}
              onNavClick={handleNavClick}
              onToggleCollapse={() => setIsSidebarOpen(false)}
              unreadMessagesCount={unreadMessagesCount}
              todayHasMatch={hasMatchToday}
              managerName={managerName}
              teamName={myTeamName}
              onNavigateSettings={handleNavigateSettings}
              isUnemployed={isUnemployed ?? false}
              onExitClick={() => {
                if (!isExitingToMenu) {
                  setShowExitConfirm(true);
                }
              }}
            />
          </div>
        </>
      ) : null}
"""
if old_sidebar_block not in dashboard:
    raise RuntimeError("Dashboard sidebar block marker not found")
dashboard = dashboard.replace(old_sidebar_block, new_sidebar_block, 1)
dashboard = dashboard.replace(
    '<main className="flex-1 flex flex-col h-screen overflow-hidden">',
    '<main className="flex h-screen w-full flex-col overflow-hidden">',
    1,
)
dashboard_path.write_text(dashboard, encoding="utf-8")

# Cabeçalho mais compacto.
header_path = root / "src" / "components" / "dashboard" / "DashboardHeader.tsx"
header = header_path.read_text(encoding="utf-8")
header = header.replace(
    '"flex items-center gap-1.5 rounded-lg px-3 py-2.5 text-sm font-heading font-bold uppercase tracking-wider transition-all hover:cursor-pointer"',
    '"flex items-center gap-1.5 rounded-lg px-2 py-2 text-[0px] font-heading font-bold uppercase tracking-wider transition-all hover:cursor-pointer sm:px-3 sm:py-2.5 sm:text-sm"',
    1,
)
header = header.replace(
    '<header className="z-10 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3 shadow-sm transition-colors duration-300 dark:border-navy-700 dark:bg-navy-800">',
    '<header className="z-10 flex items-center justify-between gap-2 border-b border-gray-200 bg-white px-3 py-2 shadow-sm transition-colors duration-300 dark:border-navy-700 dark:bg-navy-800 sm:px-4 sm:py-2.5">',
    1,
)
header = header.replace(
    '      <div className="flex items-center gap-3">\n        {hasProfileHistory',
    '      <div className="flex min-w-0 items-center gap-2 pl-11 sm:gap-3 sm:pl-12">\n        {hasProfileHistory',
    1,
)
header = header.replace(
    'className="text-xl font-heading font-bold uppercase tracking-wide text-gray-800 dark:text-gray-100"',
    'className="truncate text-base font-heading font-bold uppercase tracking-wide text-gray-800 dark:text-gray-100 sm:text-xl"',
    1,
)
header = header.replace(
    '<div className="relative mx-auto flex-1 px-10">',
    '<div className="relative mx-auto hidden flex-1 px-4 md:block lg:px-10">',
    1,
)
header = header.replace(
    '      <div className="flex items-center gap-3">\n        <ThemeToggle />',
    '      <div className="flex shrink-0 items-center gap-1.5 sm:gap-3">\n        <ThemeToggle />',
    1,
)
header_path.write_text(header, encoding="utf-8")

# Área de conteúdo mais compacta.
workspace_path = root / "src" / "components" / "dashboard" / "DashboardWorkspaceContent.tsx"
workspace = workspace_path.read_text(encoding="utf-8")
workspace = workspace.replace(
    'className="flex-1 overflow-auto p-6 bg-gray-100 dark:bg-navy-900"',
    'className="flex-1 overflow-auto bg-gray-100 p-3 dark:bg-navy-900 sm:p-4 lg:p-6"',
    1,
)
workspace = workspace.replace(
    'className="mx-6 mt-4 flex items-center gap-3',
    'className="mx-0 mt-2 flex items-center gap-3 sm:mx-2 sm:mt-3',
    1,
)
workspace_path.write_text(workspace, encoding="utf-8")

# Atributos: números no lugar de barras.
attrs_path = root / "src" / "components" / "playerProfile" / "PlayerProfileAttributesCard.tsx"
attrs = attrs_path.read_text(encoding="utf-8")
attrs = attrs.replace('import { getAttributeColors } from "../../lib/playerAttributeDisplay";\n', '')
attrs = attrs.replace(
    'import { Card, CardBody, CardHeader, ProgressBar } from "../ui";',
    'import { Card, CardBody, CardHeader } from "../ui";',
)
attrs = attrs.replace(
    'className="grid grid-cols-[auto_1fr_1.75rem] items-center gap-x-3 gap-y-2.5"',
    'className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-2.5"',
)
attrs = attrs.replace(
    """                      <ProgressBar
                        value={attr.value}
                        variant={getAttributeColors(attr.value).barVariant}
                        size="sm"
                        className="min-w-0"
                      />
""",
    "",
    1,
)
attrs = attrs.replace(
    """                        <ProgressBar
                          value={placeholderWidth(attr.name)}
                          variant="muted"
                          size="sm"
                          className="min-w-0"
                        />
""",
    "",
    1,
)
attrs = re.sub(
    r'// Deterministic placeholder bar width.*?\nfunction placeholderWidth\(name: string\): number \{.*?\n\}\n\n',
    '',
    attrs,
    flags=re.S,
)
attrs_path.write_text(attrs, encoding="utf-8")

scout_path = root / "src" / "components" / "ScoutPlayerCard.tsx"
scout = scout_path.read_text(encoding="utf-8")
scout = scout.replace(
    'import { ProgressBar, CountryFlag } from "./ui";',
    'import { CountryFlag } from "./ui";',
)
scout = scout.replace(
    """                  <>
                    <div className="flex-1">
                      <ProgressBar value={attr.value} size="sm" />
                    </div>
                    <span className="text-xs font-bold tabular-nums text-gray-700 dark:text-gray-200 w-6 text-right">
                      {attr.value}
                    </span>
                  </>
""",
    """                  <span className="ml-auto min-w-8 rounded-md bg-gray-100 px-2 py-1 text-center text-xs font-bold tabular-nums text-gray-800 dark:bg-navy-600 dark:text-gray-100">
                    {attr.value}
                  </span>
""",
    1,
)
scout_path.write_text(scout, encoding="utf-8")

# Ajustes gerais de toque/mobile
css_path = root / "src" / "App.css"
css = css_path.read_text(encoding="utf-8")
marker = "/* CM Android mobile tuning */"
if marker not in css:
    css += """
/* CM Android mobile tuning */
@media (max-width: 1023px) {
  html, body, #root { min-height: 100%; width: 100%; overflow-x: hidden; }
  button, a, [role="button"] { touch-action: manipulation; }
  .overflow-x-auto { -webkit-overflow-scrolling: touch; }
}
@media (max-width: 640px) {
  input, select, textarea { font-size: 16px; }
}
"""
css_path.write_text(css, encoding="utf-8")

print("CM Android preparado em", root)
