from pathlib import Path
import json
import re

root = Path("upstream")

# Nome do pacote/scripts Android
pkg_path = root / "package.json"
pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
pkg["name"] = "wfe-world-football-empire"
scripts = pkg.setdefault("scripts", {})
scripts["android:init"] = "tauri android init"
scripts["android:dev"] = "tauri android dev"
scripts["android:build"] = "tauri android build"
pkg_path.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Lockfile: só troca o nome do pacote raiz para manter npm ci coerente
lock_path = root / "package-lock.json"
lock = json.loads(lock_path.read_text(encoding="utf-8"))
lock["name"] = "wfe-world-football-empire"
if "" in lock.get("packages", {}):
    lock["packages"][""]["name"] = "wfe-world-football-empire"
lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Tauri / Android - versão de teste instalada ao lado do CM atual
conf_path = root / "src-tauri" / "tauri.conf.json"
conf = json.loads(conf_path.read_text(encoding="utf-8"))
conf["productName"] = "World Football Empire"
conf["identifier"] = "com.wfe.worldfootballempire.test1"
conf.setdefault("app", {}).setdefault("windows", [{}])[0]["title"] = "WFE - World Football Empire"
resources = conf.setdefault("bundle", {}).setdefault("resources", {})
resources["resources/wfe-brasil-2026-fase1.ofm"] = "packages/wfe-brasil-2026-fase1.ofm"
conf_path.write_text(json.dumps(conf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Base Brasil embutida: grava os bytes diretamente no app-data.
# Isso evita depender do resource_dir no Android, que não expôs o .ofm como esperado.
world_path = root / "src-tauri" / "src" / "commands" / "world.rs"
world_src = world_path.read_text(encoding="utf-8")
if "ensure_bundled_wfe_package" not in world_src:
    marker = """fn packages_dir(app_handle: &tauri::AppHandle) -> Result<std::path::PathBuf, String> {
    let app_data_dir = app_handle
        .path()
        .app_data_dir()
        .map_err(|e| e.to_string())?;
    Ok(app_data_dir.join("packages"))
}
"""
    helper = marker + r'''

const WFE_BRASIL_PACKAGE_BYTES: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/resources/wfe-brasil-2026-fase1.ofm"
));

fn ensure_bundled_wfe_package(app_handle: &tauri::AppHandle) -> Result<(), String> {
    let dir = packages_dir(app_handle)?;
    std::fs::create_dir_all(&dir)
        .map_err(|_| "be.error.package.installFailed".to_string())?;
    let dest = dir.join("wfe-brasil-2026-fase1.ofm");

    let should_write = match std::fs::metadata(&dest) {
        Ok(meta) => meta.len() != WFE_BRASIL_PACKAGE_BYTES.len() as u64,
        Err(_) => true,
    };

    if should_write {
        std::fs::write(&dest, WFE_BRASIL_PACKAGE_BYTES)
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
    list_repl = list_marker + """    ensure_bundled_wfe_package(&app_handle)?;
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
    data.setdefault("app", {})["name"] = "World Football Empire"
    data.setdefault("app", {})["publisher"] = "World Football Empire"
    locale_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Título da janela
app_path = root / "src" / "App.tsx"
app = app_path.read_text(encoding="utf-8")
app = app.replace(
    'await getCurrentWindow().setTitle(`Openfoot Manager ${formatAppVersion()}`);',
    'await getCurrentWindow().setTitle(`WFE - World Football Empire ${formatAppVersion()}`);',
)
app_path.write_text(app, encoding="utf-8")

# Identidade visual WFE - World Football Empire
logo = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 360" role="img" aria-labelledby="title desc">
  <title id="title">WFE</title>
  <desc id="desc">World Football Empire</desc>
  <defs>
    <linearGradient id="wfeG" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#16c784"/>
      <stop offset="1" stop-color="#d6df32"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="360" rx="46" fill="#101a33"/>
  <path d="M180 44 298 92v98c0 70-46 112-118 134C108 302 62 260 62 190V92Z" fill="url(#wfeG)"/>
  <path d="M104 121h152v49H104zm0 69h152v49H104z" fill="#101a33" opacity=".92"/>
  <text x="362" y="208" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="146" fill="#fff">WFE</text>
  <text x="370" y="278" font-family="Arial,Helvetica,sans-serif" font-weight="700" font-size="34" fill="#a9b4ca" letter-spacing="10">WORLD FOOTBALL EMPIRE</text>
</svg>
"""
(root / "public" / "wfe-logo.svg").write_text(logo, encoding="utf-8")

app_icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#16c784"/>
      <stop offset="1" stop-color="#d6df32"/>
    </linearGradient>
  </defs>
  <rect width="1024" height="1024" rx="220" fill="#101a33"/>
  <path d="M512 116 792 228v230c0 190-111 335-280 410-169-75-280-220-280-410V228Z" fill="url(#g)"/>
  <text x="512" y="585" text-anchor="middle" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="238" fill="#101a33">WFE</text>
</svg>
"""
(root / "public" / "wfe-app-icon.svg").write_text(app_icon, encoding="utf-8")

# Browser/index branding
index_path = root / "index.html"
index_src = index_path.read_text(encoding="utf-8")
index_src = index_src.replace(
    '<link rel="icon" type="image/png" href="/openfootmanager_icon.png" />',
    '<link rel="icon" type="image/svg+xml" href="/wfe-app-icon.svg" />',
)
index_src = index_src.replace("<title>Openfoot Manager</title>", "<title>WFE - World Football Empire</title>")
index_path.write_text(index_src, encoding="utf-8")

# Startup log branding (not gameplay logic).
main_ts_path = root / "src" / "main.tsx"
main_ts = main_ts_path.read_text(encoding="utf-8")
main_ts = main_ts.replace(
    'logInfo(\`[startup] Openfoot Manager \${formatAppVersion()} (\${navigator.userAgent})\`);',
    'logInfo(\`[startup] WFE - World Football Empire \${formatAppVersion()} (\${navigator.userAgent})\`);',
)
main_ts_path.write_text(main_ts, encoding="utf-8")

menu_path = root / "src" / "pages" / "MainMenu.tsx"
menu = menu_path.read_text(encoding="utf-8")
menu = menu.replace('src="/openfootlogo.svg"', 'src="/wfe-logo.svg"')
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
        className="fixed left-3 top-3 z-30 flex h-12 w-12 items-center justify-center rounded-xl bg-navy-800 text-white shadow-lg ring-1 ring-white/10 active:scale-95"
      >
        <Menu className="h-6 w-6" />
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
header = header.replace('  Calendar as CalendarIcon,\n', '', 1)
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

# Perfil do jogador CM: topo compacto + navegação por cards/abas.
# Mantém todas as funções existentes, mas exibe somente uma seção por vez
# para evitar uma página longa no celular. Atributos é a seção inicial.
profile_path = root / "src" / "components" / "playerProfile" / "PlayerProfile.tsx"
profile = profile_path.read_text(encoding="utf-8")
profile = profile.replace(
    'import { ArrowLeft } from "lucide-react";',
    'import { ArrowLeft, BarChart3, Briefcase, CalendarDays, Clock3, History, ListChecks, SlidersHorizontal } from "lucide-react";',
    1,
)
profile = profile.replace(
    'import { useTranslation } from "react-i18next";',
    'import { useState } from "react";\nimport { useTranslation } from "react-i18next";',
    1,
)
profile = profile.replace(
    'import { Select } from "../ui";',
    'import { Card, CardBody, CardHeader, Select } from "../ui";',
    1,
)
profile = profile.replace(
    '  const { t, i18n } = useTranslation();\n',
    '''  const { t, i18n } = useTranslation();
  const [activeProfileSection, setActiveProfileSection] = useState<
    | "attributes"
    | "contract"
    | "role"
    | "career"
    | "advanced"
    | "season"
    | "movement"
    | "recent"
  >("attributes");
''',
    1,
)

return_marker = '  return (\n    <div>\n'
sections_code = '''  const profileSections = [
    { id: "attributes", label: t("playerProfile.attributes"), icon: BarChart3 },
    { id: "contract", label: t("playerProfile.contractInfo"), icon: Briefcase },
    { id: "role", label: t("playerProfile.roleAndDuty"), icon: SlidersHorizontal },
    { id: "career", label: t("playerProfile.careerHistory"), icon: History },
    { id: "advanced", label: t("playerProfile.advancedStats"), icon: BarChart3 },
    { id: "season", label: t("playerProfile.seasonHistory"), icon: CalendarDays },
    { id: "movement", label: t("playerProfile.movementHistory"), icon: ListChecks },
    { id: "recent", label: t("playerProfile.recentMatches"), icon: Clock3 },
  ] as const;

  return (
    <div>
'''
if return_marker not in profile:
    raise RuntimeError("PlayerProfile return marker not found")
profile = profile.replace(return_marker, sections_code, 1)

section_start = profile.find('      {isOwnClub && onGameUpdate && (')
section_end = profile.find('      {bidTarget && (', section_start)
if section_start < 0 or section_end < 0:
    raise RuntimeError("PlayerProfile content markers not found")

tabbed_content = r'''      <div className="mb-4 overflow-x-auto pb-1">
        <div className="flex min-w-max gap-1.5">
          {profileSections.map((section) => {
            const Icon = section.icon;
            const selected = activeProfileSection === section.id;
            return (
              <button
                key={section.id}
                type="button"
                onClick={() => setActiveProfileSection(section.id)}
                aria-pressed={selected}
                className={`flex h-16 w-24 shrink-0 flex-col items-center justify-center gap-1 rounded-xl border px-1.5 py-1.5 text-center transition-all sm:h-20 sm:w-32 sm:gap-1.5 sm:px-2 sm:py-2 ${
                  selected
                    ? "border-primary-400 bg-primary-500/15 text-primary-500 shadow-sm dark:text-primary-300"
                    : "border-gray-200 bg-white text-gray-500 hover:border-primary-300 hover:text-primary-500 dark:border-navy-600 dark:bg-navy-800 dark:text-gray-400"
                }`}
              >
                <Icon className="h-4 w-4 sm:h-5 sm:w-5" />
                <span className="line-clamp-2 text-[9px] font-heading font-bold leading-tight uppercase tracking-wide sm:text-[11px]">
                  {section.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {contractActionError ? (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
          {contractActionError}
        </div>
      ) : null}

      {activeProfileSection === "attributes" ? (
        <PlayerProfileAttributesCard
          attrGroups={attrGroups}
          player={player}
          isOwnClub={isManagerSquadProfile}
          isGk={isGoalkeeper(player)}
          title={t("playerProfile.attributes")}
          averageLabel={t("common.average")}
          hiddenTitle={t("playerProfile.attributesHidden")}
          hiddenBody={t("playerProfile.scoutToView")}
          listLabel={t("common.listView")}
          radarLabel={t("common.radarView")}
        />
      ) : null}

      {activeProfileSection === "contract" ? (
        <PlayerProfileContractCard
          dateOfBirth={player.date_of_birth}
          contractEnd={player.contract_end}
          currentDate={gameState.clock.current_date}
          condition={player.condition}
          morale={player.morale}
          marketValue={player.market_value}
          wage={player.wage}
          wageSuffix={weeklySuffix}
          language={i18n.language}
          contractRiskLevel={contractRiskLevel}
          contractRiskLabel={contractRiskLabel}
          isOwnClub={isManagerOwnedProfile}
          isFreeAgent={isFreeAgent}
          hasLetExpireIntent={hasLetExpireIntent}
          actionSubmitting={contractActionSubmitting}
          onOpenRenewal={openRenewalModal}
          onMarkLetExpire={() => void handleMarkLetExpire()}
          onClearLetExpire={() => void handleClearLetExpire()}
          onOpenTermination={() => void openTerminationModal()}
          onOpenFreeAgentContract={() => openFreeAgentContract(player)}
          t={t}
        />
      ) : null}

      {activeProfileSection === "role" ? (
        <Card>
          <CardHeader>{t("playerProfile.roleAndDuty")}</CardHeader>
          <CardBody>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-3 dark:border-navy-600 dark:bg-navy-700/40">
                <p className="text-[10px] font-heading font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                  {t("tactics.playerRoleLabel")}
                </p>
                <p className="mt-1 font-heading font-bold text-gray-800 dark:text-gray-100">
                  {t(`tactics.playerRoles.${currentTacticalRole}`, currentTacticalRole)}
                </p>
              </div>

              {isOwnClub && onGameUpdate ? (
                <div className="rounded-xl border border-gray-100 bg-gray-50 p-3 dark:border-navy-600 dark:bg-navy-700/40">
                  <p className="mb-2 text-[10px] font-heading font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    {t("playerProfile.changeRole")}
                  </p>
                  <Select
                    selectSize="sm"
                    value={currentTacticalRole}
                    onChange={(e) => {
                      void handleTacticalRoleChange(e.target.value as PlayerRole);
                    }}
                    aria-label={t("tactics.playerRoleLabel")}
                  >
                    {tacticalRoleOptions.map((role) => (
                      <option key={role} value={role}>
                        {t(`tactics.playerRoles.${role}`, role)}
                      </option>
                    ))}
                  </Select>
                </div>
              ) : null}
            </div>
          </CardBody>
        </Card>
      ) : null}

      {activeProfileSection === "career" ? (
        <PlayerProfileCareerHistoryCard career={player.career} t={t} />
      ) : null}

      {activeProfileSection === "advanced" ? (
        <PlayerProfileAdvancedStatsCard summary={advancedStats} t={t} />
      ) : null}

      {activeProfileSection === "season" ? (
        <PlayerProfileSeasonStatsCard stats={player.stats} t={t} />
      ) : null}

      {activeProfileSection === "movement" ? (
        <PlayerProfileMovementHistoryCard movementHistory={player.movement_history ?? []} t={t} />
      ) : null}

      {activeProfileSection === "recent" ? (
        recentMatches.length > 0 ? (
          <PlayerProfileRecentMatchesCard matches={recentMatches} t={t} />
        ) : (
          <Card>
            <CardHeader>{t("playerProfile.recentMatches")}</CardHeader>
            <CardBody>
              <p className="py-5 text-center text-sm text-gray-400 dark:text-gray-500">
                {t("playerProfile.noRecentMatches")}
              </p>
            </CardBody>
          </Card>
        )
      ) : null}

'''
profile = profile[:section_start] + tabbed_content + profile[section_end:]
profile_path.write_text(profile, encoding="utf-8")

# Hero do jogador mais compacto, preservando os mesmos dados/ações.
hero_path = root / "src" / "components" / "playerProfile" / "PlayerProfileHeroCard.tsx"
hero = hero_path.read_text(encoding="utf-8")
hero = hero.replace('className="mb-5"', 'className="mb-3"', 1)
hero = hero.replace(
    'className="bg-linear-to-r from-navy-700 to-navy-800 p-8 rounded-t-xl"',
    'className="rounded-t-xl bg-linear-to-r from-navy-700 to-navy-800 p-3 sm:p-5"',
    1,
)
hero = hero.replace(
    'className="flex items-start gap-6"',
    'className="flex items-start gap-3 sm:gap-4"',
    1,
)
hero = hero.replace(
    'className={`w-24 h-24 rounded-2xl flex items-center justify-center font-heading font-bold text-4xl border-2 overflow-hidden ${',
    'className={`h-16 w-16 shrink-0 rounded-xl flex items-center justify-center font-heading font-bold text-xl sm:h-24 sm:w-24 sm:rounded-2xl sm:text-4xl border-2 overflow-hidden ${',
    1,
)
hero = hero.replace(
    'className="text-3xl font-heading font-bold text-white uppercase tracking-wide"',
    'className="text-lg font-heading font-bold text-white uppercase tracking-wide sm:text-2xl"',
    1,
)
hero = hero.replace(
    'className="flex items-center gap-3 mt-2"',
    'className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-0.5"',
    1,
)
hero = hero.replace(
    'className="bg-white dark:bg-navy-800 p-3 text-center"',
    'className="bg-white p-1.5 text-center dark:bg-navy-800 sm:p-3"',
)
hero = hero.replace(
    'className="text-xs text-gray-400 dark:text-gray-500 font-heading uppercase tracking-wider"',
    'className="text-[8px] text-gray-400 dark:text-gray-500 font-heading uppercase tracking-wider sm:text-xs"',
)
hero = hero.replace(
    'className={`font-heading font-bold text-lg mt-0.5 ${color}`}',
    'className={`mt-0.5 font-heading text-xs font-bold sm:text-lg ${color}`}',
)
hero_path.write_text(hero, encoding="utf-8")

# Atributos no padrão do esboço: três colunas para jogadores de linha,
# duas colunas para goleiros (que possuem um quarto grupo).
attrs = attrs_path.read_text(encoding="utf-8")
attrs = attrs.replace(
    'className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:auto-rows-fr"',
    'className={`grid gap-1.5 sm:gap-3 ${isGk ? "grid-cols-2" : "grid-cols-3"}`}',
)
attrs = attrs.replace(
    'className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-2.5"',
    'className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-1 gap-y-1"',
)
attrs = attrs.replace(
    'className="text-xs text-gray-600 dark:text-gray-400 whitespace-nowrap"',
    'className="min-w-0 text-[9px] leading-none text-gray-600 dark:text-gray-400 sm:text-xs"',
)
attrs = attrs.replace(
    'className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap"',
    'className="min-w-0 text-[9px] leading-none text-gray-400 dark:text-gray-500 sm:text-xs"',
)
attrs = attrs.replace(
    '<CardHeader',
    '<CardHeader className="!px-3 !py-2 sm:!px-4 sm:!py-3"',
    1,
)
attrs = attrs.replace(
    '<CardBody>',
    '<CardBody className="!p-2 !pb-8 sm:!p-4">',
    1,
)
attrs_path.write_text(attrs, encoding="utf-8")

# Ordem visual aprovada: Técnicos, Mentais, Físicos (e Goleiro, quando aplicável).
attribute_meta_path = root / "src" / "components" / "playerProfile" / "PlayerProfile.attributes.ts"
attribute_meta = attribute_meta_path.read_text(encoding="utf-8")
attribute_meta = attribute_meta.replace(
    'const GROUP_ORDER: readonly AttributeGroupKey[] = ["physical", "technical", "mental", "goalkeeper"];',
    'const GROUP_ORDER: readonly AttributeGroupKey[] = ["technical", "mental", "physical", "goalkeeper"];',
    1,
)
attribute_meta_path.write_text(attribute_meta, encoding="utf-8")

# Cards estatísticos mais compactos no mobile.
stat_card_path = root / "src" / "components" / "playerProfile" / "PlayerProfileStatCard.tsx"
stat_card = stat_card_path.read_text(encoding="utf-8")
stat_card = stat_card.replace(
    'dark:bg-navy-800/40 p-4">',
    'dark:bg-navy-800/40 p-1.5 sm:p-3">',
    1,
)
stat_card = stat_card.replace(
    'className="flex items-baseline justify-between mb-3 pb-2 border-b',
    'className="mb-1.5 flex items-baseline justify-between border-b pb-1',
    1,
)
stat_card_path.write_text(stat_card, encoding="utf-8")

# Rótulos pt-BR específicos das novas abas.
ptbr_path = root / "src" / "i18n" / "locales" / "pt-BR.json"
ptbr = json.loads(ptbr_path.read_text(encoding="utf-8"))
player_profile_labels = ptbr.setdefault("playerProfile", {})
player_profile_labels["roleAndDuty"] = "Função e papel"
player_profile_labels["changeRole"] = "Alterar função"
player_profile_labels["seasonHistory"] = "Histórico da temporada"
ptbr_path.write_text(json.dumps(ptbr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

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


# Primeiros Passos: pode ser dispensado depois de lido e não volta nessa carreira.
home_path = root / "src" / "components" / "home" / "HomeTab.tsx"
home = home_path.read_text(encoding="utf-8")
if 'cm-onboarding-dismissed' not in home:
    home = 'import { useEffect, useState } from "react";\n' + home
    home = home.replace(
        '  const { t, i18n } = useTranslation();\n',
        '''  const { t, i18n } = useTranslation();
  const onboardingDismissKey =
    `cm-onboarding-dismissed:${gameState.manager.id}:${gameState.clock.start_date}`;
  const [onboardingDismissed, setOnboardingDismissed] = useState(() =>
    typeof window !== "undefined" &&
    window.localStorage.getItem(onboardingDismissKey) === "1",
  );

  useEffect(() => {
    setOnboardingDismissed(
      typeof window !== "undefined" &&
        window.localStorage.getItem(onboardingDismissKey) === "1",
    );
  }, [onboardingDismissKey]);

  const dismissOnboarding = () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(onboardingDismissKey, "1");
    }
    setOnboardingDismissed(true);
  };
''',
        1,
    )
    home = home.replace(
        '{myTeam && onboardingState.showOnboarding && completedSteps < onboardingSteps.length && (',
        '{myTeam && !onboardingDismissed && onboardingState.showOnboarding && completedSteps < onboardingSteps.length && (',
        1,
    )
    home = home.replace(
        '          onNavigate={onNavigate}\n        />',
        '          onNavigate={onNavigate}\n          onDismiss={dismissOnboarding}\n        />',
        1,
    )
home_path.write_text(home, encoding="utf-8")

onboarding_card_path = root / "src" / "components" / "home" / "HomeOnboardingChecklistCard.tsx"
onboarding_card = onboarding_card_path.read_text(encoding="utf-8")
if 'onDismiss?: () => void;' not in onboarding_card:
    onboarding_card = onboarding_card.replace(
        'import { CheckCircle2, Circle, Lightbulb } from "lucide-react";',
        'import { CheckCircle2, Circle, Lightbulb, X } from "lucide-react";',
        1,
    )
    onboarding_card = onboarding_card.replace(
        '  onNavigate?: (tab: string) => void;\n}',
        '  onNavigate?: (tab: string) => void;\n  onDismiss?: () => void;\n}',
        1,
    )
    onboarding_card = onboarding_card.replace(
        '  onNavigate,\n}: HomeOnboardingChecklistCardProps) {',
        '  onNavigate,\n  onDismiss,\n}: HomeOnboardingChecklistCardProps) {',
        1,
    )
    onboarding_card = onboarding_card.replace(
        '      <CardHeader>\n        <div className="flex items-center gap-2">',
        '''      <CardHeader
        action={
          onDismiss ? (
            <button
              type="button"
              onClick={onDismiss}
              aria-label={t("common.close")}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:text-gray-500 dark:hover:bg-navy-600 dark:hover:text-gray-200"
            >
              <X className="h-5 w-5" />
            </button>
          ) : undefined
        }
      >
        <div className="flex items-center gap-2">''',
        1,
    )
onboarding_card_path.write_text(onboarding_card, encoding="utf-8")


# Tela inicial CM: identidade do clube + Próxima Partida + Caixa de Entrada + Próximos Jogos.
cm_home_path = root / "src" / "components" / "home" / "CMHomeDashboard.tsx"
cm_home_path.write_text("import { CalendarDays, ChevronRight, House, Mail, Plane } from \"lucide-react\";\nimport { useTranslation } from \"react-i18next\";\n\nimport {\n  formatDateShort,\n  getFixtureCompetitionName,\n  getTeamName,\n} from \"../../lib/helpers\";\nimport type { FixtureData, GameStateData, MessageData } from \"../../store/gameStore\";\nimport { isMessageVisible } from \"../../utils/newsVisibility\";\nimport { Card, TeamLogo } from \"../ui\";\n\ninterface CMHomeDashboardProps {\n  gameState: GameStateData;\n  messages: MessageData[];\n  lang: string;\n  onNavigate?: (tab: string, context?: { messageId?: string }) => void;\n}\n\ntype UpcomingEntry = {\n  fixture: FixtureData;\n  competitionName: string;\n};\n\nfunction formatFixtureDay(date: string, lang: string): string {\n  const parsed = new Date(`${date}T12:00:00`);\n  if (Number.isNaN(parsed.getTime())) return date;\n  return new Intl.DateTimeFormat(lang || \"pt-BR\", {\n    day: \"2-digit\",\n    month: \"2-digit\",\n    weekday: \"short\",\n  }).format(parsed);\n}\n\nexport default function CMHomeDashboard({\n  gameState,\n  messages,\n  lang,\n  onNavigate,\n}: CMHomeDashboardProps) {\n  const { t } = useTranslation();\n  const teamId = gameState.manager.team_id;\n  const team = teamId ? gameState.teams.find((item) => item.id === teamId) ?? null : null;\n\n  const byId = new Map<string, UpcomingEntry>();\n  if (teamId) {\n    for (const competition of gameState.competitions ?? []) {\n      for (const fixture of competition.fixtures ?? []) {\n        if (\n          fixture.status !== \"Scheduled\" ||\n          (fixture.home_team_id !== teamId && fixture.away_team_id !== teamId)\n        ) {\n          continue;\n        }\n        if (!byId.has(fixture.id)) {\n          byId.set(fixture.id, {\n            fixture,\n            competitionName: getFixtureCompetitionName(gameState, fixture, t) ?? \"\",\n          });\n        }\n      }\n    }\n  }\n\n  const upcoming = Array.from(byId.values())\n    .sort((left, right) =>\n      left.fixture.date.localeCompare(right.fixture.date) ||\n      left.fixture.matchday - right.fixture.matchday,\n    )\n    .slice(0, 3);\n\n  const nextEntry = upcoming[0] ?? null;\n  const nextFixture = nextEntry?.fixture ?? null;\n  const homeTeam = nextFixture\n    ? gameState.teams.find((item) => item.id === nextFixture.home_team_id) ?? null\n    : null;\n  const awayTeam = nextFixture\n    ? gameState.teams.find((item) => item.id === nextFixture.away_team_id) ?? null\n    : null;\n\n  const visibleMessages = messages\n    .filter((message) => isMessageVisible(message.date, gameState.clock.current_date))\n    .slice(0, 3);\n  const unreadCount = gameState.messages.filter(\n    (message) => !message.read && isMessageVisible(message.date, gameState.clock.current_date),\n  ).length;\n\n  return (\n    <div className=\"cm-home flex flex-col gap-3 pb-4\">\n      {team ? (\n        <button\n          type=\"button\"\n          onClick={() => onNavigate?.(\"Squad\")}\n          className=\"relative overflow-hidden rounded-2xl border border-white/10 px-4 py-3 text-left shadow-sm\"\n          style={{\n            background: `linear-gradient(125deg, ${team.colors.primary} 0%, ${team.colors.secondary} 100%)`,\n          }}\n        >\n          <div className=\"relative z-10 flex items-center gap-3\">\n            <TeamLogo\n              team={team}\n              className=\"flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-white/10\"\n              imageClassName=\"h-12 w-12 object-contain drop-shadow\"\n            />\n            <div className=\"min-w-0\">\n              <p className=\"truncate font-heading text-lg font-bold uppercase tracking-wide text-white\">\n                {team.name}\n              </p>\n              <p className=\"mt-0.5 text-xs font-medium uppercase tracking-wider text-white/75\">\n                {team.country}\n              </p>\n            </div>\n            <ChevronRight className=\"ml-auto h-5 w-5 shrink-0 text-white/70\" />\n          </div>\n          <div className=\"absolute inset-y-0 right-0 w-2/5 -skew-x-12 bg-black/15\" />\n        </button>\n      ) : null}\n\n      <Card className=\"overflow-hidden\">\n        <button\n          type=\"button\"\n          onClick={() => onNavigate?.(\"Schedule\")}\n          className=\"flex w-full items-center gap-3 border-b border-gray-100 px-4 py-3 text-left dark:border-navy-600\"\n        >\n          <span className=\"flex h-9 w-9 items-center justify-center rounded-lg bg-primary-500/15 text-primary-400\">\n            <CalendarDays className=\"h-5 w-5\" />\n          </span>\n          <span className=\"font-heading text-base font-bold uppercase tracking-wide text-gray-800 dark:text-gray-100\">\n            Próxima Partida\n          </span>\n          <span className=\"ml-auto max-w-[42%] truncate text-xs text-gray-400\">\n            {nextEntry?.competitionName ?? \"\"}\n          </span>\n          <ChevronRight className=\"h-4 w-4 text-gray-400\" />\n        </button>\n\n        {nextFixture && homeTeam && awayTeam ? (\n          <div className=\"grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-3 py-4\">\n            <div className=\"min-w-0 text-center\">\n              <TeamLogo\n                team={homeTeam}\n                className=\"mx-auto flex h-14 w-14 items-center justify-center overflow-hidden rounded-xl bg-white/5\"\n                imageClassName=\"h-12 w-12 object-contain drop-shadow\"\n              />\n              <p className=\"mt-1 truncate font-heading text-xs font-bold uppercase text-gray-800 dark:text-gray-100\">\n                {homeTeam.short_name || homeTeam.name}\n              </p>\n            </div>\n\n            <div className=\"px-1 text-center\">\n              <p className=\"text-[10px] font-semibold uppercase tracking-wider text-gray-400\">\n                {formatFixtureDay(nextFixture.date, lang)}\n              </p>\n              <p className=\"mt-1 font-heading text-xl font-black text-gray-800 dark:text-white\">VS</p>\n              <p className=\"mt-1 text-[10px] text-gray-400\">\n                {homeTeam.stadium_name || t(\"common.unknown\")}\n              </p>\n            </div>\n\n            <div className=\"min-w-0 text-center\">\n              <TeamLogo\n                team={awayTeam}\n                className=\"mx-auto flex h-14 w-14 items-center justify-center overflow-hidden rounded-xl bg-white/5\"\n                imageClassName=\"h-12 w-12 object-contain drop-shadow\"\n              />\n              <p className=\"mt-1 truncate font-heading text-xs font-bold uppercase text-gray-800 dark:text-gray-100\">\n                {awayTeam.short_name || awayTeam.name}\n              </p>\n            </div>\n          </div>\n        ) : (\n          <p className=\"px-4 py-6 text-center text-sm text-gray-400\">\n            {t(\"home.noUpcomingOpponent\")}\n          </p>\n        )}\n      </Card>\n\n      <Card className=\"overflow-hidden\">\n        <button\n          type=\"button\"\n          onClick={() => onNavigate?.(\"Inbox\")}\n          className=\"flex w-full items-center gap-3 border-b border-gray-100 px-4 py-3 text-left dark:border-navy-600\"\n        >\n          <span className=\"flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/15 text-blue-400\">\n            <Mail className=\"h-5 w-5\" />\n          </span>\n          <span className=\"font-heading text-base font-bold uppercase tracking-wide text-gray-800 dark:text-gray-100\">\n            Caixa de Entrada\n          </span>\n          <span className=\"ml-auto text-xs text-gray-400\">\n            {unreadCount > 0 ? `${unreadCount} não lida${unreadCount === 1 ? \"\" : \"s\"}` : \"Sem novas\"}\n          </span>\n          <ChevronRight className=\"h-4 w-4 text-gray-400\" />\n        </button>\n\n        <div className=\"divide-y divide-gray-100 dark:divide-navy-600\">\n          {visibleMessages.length > 0 ? (\n            visibleMessages.map((message) => (\n              <button\n                type=\"button\"\n                key={message.id}\n                onClick={() => onNavigate?.(\"Inbox\", { messageId: message.id })}\n                className=\"flex w-full items-start gap-3 px-4 py-2.5 text-left transition-colors hover:bg-gray-50 dark:hover:bg-navy-600/40\"\n              >\n                <span\n                  className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${message.read ? \"bg-gray-300 dark:bg-navy-500\" : \"bg-primary-400\"}`}\n                />\n                <span className=\"min-w-0 flex-1\">\n                  <span className=\"block truncate text-sm font-semibold text-gray-800 dark:text-gray-100\">\n                    {message.subject}\n                  </span>\n                  <span className=\"mt-0.5 block truncate text-xs text-gray-400\">\n                    {message.body}\n                  </span>\n                </span>\n                <span className=\"shrink-0 text-[10px] text-gray-400\">\n                  {formatDateShort(message.date, lang)}\n                </span>\n              </button>\n            ))\n          ) : (\n            <p className=\"px-4 py-5 text-center text-sm text-gray-400\">{t(\"home.noMessages\")}</p>\n          )}\n        </div>\n      </Card>\n\n      <Card className=\"overflow-hidden\">\n        <button\n          type=\"button\"\n          onClick={() => onNavigate?.(\"Schedule\")}\n          className=\"flex w-full items-center gap-3 border-b border-gray-100 px-4 py-3 text-left dark:border-navy-600\"\n        >\n          <span className=\"flex h-9 w-9 items-center justify-center rounded-lg bg-primary-500/15 text-primary-400\">\n            <CalendarDays className=\"h-5 w-5\" />\n          </span>\n          <span className=\"font-heading text-base font-bold uppercase tracking-wide text-gray-800 dark:text-gray-100\">\n            Próximos Jogos\n          </span>\n          <span className=\"ml-auto text-xs text-gray-400\">Todos os jogos</span>\n          <ChevronRight className=\"h-4 w-4 text-gray-400\" />\n        </button>\n\n        <div className=\"divide-y divide-gray-100 dark:divide-navy-600\">\n          {upcoming.length > 0 ? (\n            upcoming.map(({ fixture, competitionName }) => {\n              const isHome = fixture.home_team_id === teamId;\n              const opponentId = isHome ? fixture.away_team_id : fixture.home_team_id;\n              const opponent = gameState.teams.find((item) => item.id === opponentId) ?? null;\n              return (\n                <button\n                  type=\"button\"\n                  key={fixture.id}\n                  onClick={() => onNavigate?.(\"Schedule\")}\n                  className=\"grid w-full grid-cols-[4.2rem_minmax(0,1fr)_1.5rem_minmax(0,1fr)] items-center gap-2 px-4 py-2.5 text-left transition-colors hover:bg-gray-50 dark:hover:bg-navy-600/40\"\n                >\n                  <span className=\"text-xs font-bold text-gray-700 dark:text-gray-200\">\n                    {formatFixtureDay(fixture.date, lang)}\n                  </span>\n                  <span className=\"truncate text-xs text-gray-500 dark:text-gray-400\">\n                    {competitionName}\n                  </span>\n                  <span className=\"flex justify-center text-gray-400\">\n                    {isHome ? <House className=\"h-4 w-4\" /> : <Plane className=\"h-4 w-4\" />}\n                  </span>\n                  <span className=\"flex min-w-0 items-center gap-2\">\n                    {opponent ? (\n                      <TeamLogo\n                        team={opponent}\n                        className=\"flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-md bg-white/5\"\n                        imageClassName=\"h-6 w-6 object-contain\"\n                      />\n                    ) : null}\n                    <span className=\"truncate text-sm font-semibold text-gray-700 dark:text-gray-200\">\n                      {opponent ? getTeamName(gameState.teams, opponent.id) : t(\"common.unknown\")}\n                    </span>\n                  </span>\n                </button>\n              );\n            })\n          ) : (\n            <p className=\"px-4 py-5 text-center text-sm text-gray-400\">\n              {t(\"home.noUpcomingOpponent\")}\n            </p>\n          )}\n        </div>\n      </Card>\n    </div>\n  );\n}\n", encoding="utf-8")

home_path = root / "src" / "components" / "home" / "HomeTab.tsx"
home = home_path.read_text(encoding="utf-8")
if 'import CMHomeDashboard from "./CMHomeDashboard";' not in home:
    home = home.replace(
        'import JobOpportunitiesCard from "./JobOpportunitiesCard";',
        'import JobOpportunitiesCard from "./JobOpportunitiesCard";\nimport CMHomeDashboard from "./CMHomeDashboard";',
        1,
    )
if 'return <CMHomeDashboard' not in home:
    home = home.replace(
        '  const hasMomentum = roster.length > 0 && (hotPlayers.length > 0 || coldPlayers.length > 0);\n\n  return (',
        '''  const hasMomentum = roster.length > 0 && (hotPlayers.length > 0 || coldPlayers.length > 0);

  return <CMHomeDashboard
    gameState={gameState}
    messages={recentMessages}
    lang={lang}
    onNavigate={onNavigate}
  />;

  return (''',
        1,
    )
home = home.replace(
    'onGameUpdate={onGameUpdate}',
    'onGameUpdate={onGameUpdate!}',
)
home_path.write_text(home, encoding="utf-8")

# Navegação inferior mobile fixa: Início | Elenco | Tática | Staff.
dashboard_path = root / "src" / "pages" / "Dashboard.tsx"
dashboard = dashboard_path.read_text(encoding="utf-8")
dashboard = dashboard.replace(
    'import { Cpu, Eye, Gamepad2, Menu } from "lucide-react";',
    'import { Cpu, Eye, Gamepad2, Menu, House, Users, Crosshair, UserCog } from "lucide-react";',
    1,
)
if 'cm-mobile-bottom-nav' not in dashboard:
    dashboard = dashboard.replace(
        '''      </main>
    </div>
  );
}''',
        '''      </main>

      <nav
        className="cm-mobile-bottom-nav fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-gray-200 bg-white/95 shadow-2xl backdrop-blur dark:border-navy-600 dark:bg-navy-800/95 lg:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        {[
          { tab: "Home", label: t("dashboard.home"), icon: House },
          { tab: "Squad", label: t("dashboard.squad"), icon: Users },
          { tab: "Tactics", label: t("dashboard.tactics"), icon: Crosshair },
          { tab: "Staff", label: "Staff", icon: UserCog },
        ].map((item) => {
          const Icon = item.icon;
          const active = profileNavigation.activeTab === item.tab;
          return (
            <button
              key={item.tab}
              type="button"
              onClick={() => handleNavClick(item.tab)}
              className={`flex min-h-16 flex-col items-center justify-center gap-1 px-1 py-2 font-heading text-[10px] font-bold uppercase tracking-wide transition-colors ${
                active
                  ? "border-t-2 border-primary-400 bg-primary-500/10 text-primary-500 dark:text-primary-300"
                  : "text-gray-500 dark:text-gray-400"
              }`}
            >
              <Icon className="h-5 w-5" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}''',
        1,
    )
dashboard_path.write_text(dashboard, encoding="utf-8")

workspace_path = root / "src" / "components" / "dashboard" / "DashboardWorkspaceContent.tsx"
workspace = workspace_path.read_text(encoding="utf-8")
workspace = workspace.replace(
    'className="flex-1 overflow-auto bg-gray-100 p-3 dark:bg-navy-900 sm:p-4 lg:p-6"',
    'className="flex-1 overflow-auto bg-gray-100 p-3 pb-24 dark:bg-navy-900 sm:p-4 sm:pb-24 lg:p-6 lg:pb-6"',
    1,
)
workspace_path.write_text(workspace, encoding="utf-8")

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


# Elenco mobile compacto: remove filtros/resumo visual e enxuga a tabela.
squad_path = root / "src" / "components" / "squad" / "SquadRosterView.tsx"
squad = squad_path.read_text(encoding="utf-8")

def _wrap_hidden_block(source: str, start_marker: str, end_marker: str, end_inclusive: bool = False) -> str:
    start = source.find(start_marker)
    if start < 0:
        return source
    end = source.find(end_marker, start)
    if end < 0:
        return source
    if end_inclusive:
        end += len(end_marker)
    block = source[start:end]
    return source[:start] + "{false && (\n" + block + "\n)}" + source[end:]

# Remove visualmente o card inteiro de pesquisa/filtros/contadores.
first_card = '      <Card>\n        <div className="p-4 grid grid-cols-1 lg:grid-cols-[minmax(0,1.3fr)_220px_220px_auto] gap-3 items-end">'
second_card = '      <Card>\n        <div className="p-4 border-b border-gray-100 dark:border-navy-600 bg-linear-to-r from-navy-700 to-navy-800 rounded-t-xl">'
first_start = squad.find(first_card)
second_start = squad.find(second_card, first_start + 1) if first_start >= 0 else -1
if first_start >= 0 and second_start >= 0:
    first_block = squad[first_start:second_start]
    squad = squad[:first_start] + "      {false && (\n" + first_block + "      )}\n\n" + squad[second_start:]

# Remove visualmente o cabeçalho/card "Elenco do [clube]" e cobertura de funções.
header_start_marker = '        <div className="p-4 border-b border-gray-100 dark:border-navy-600 bg-linear-to-r from-navy-700 to-navy-800 rounded-t-xl">'
table_start_marker = '        <div className="overflow-x-auto">'
header_start = squad.find(header_start_marker)
table_start = squad.find(table_start_marker, header_start + 1) if header_start >= 0 else -1
if header_start >= 0 and table_start >= 0:
    header_block = squad[header_start:table_start]
    squad = squad[:header_start] + "        {false && (\n" + header_block + "        )}\n" + squad[table_start:]

# Oculta as colunas de encaixe na formação, encaixe no estilo e contrato.
for col in ("fit", "style", "contract"):
    start_marker = f'                <SquadSortHeader\n                  col="{col}"'
    start = squad.find(start_marker)
    if start >= 0:
        end = squad.find('                />', start)
        if end >= 0:
            end += len('                />')
            block = squad[start:end]
            squad = squad[:start] + "                {false && (\n" + block + "\n                )}" + squad[end:]

formation_comment = '                      {/* Formation fit:'
style_comment = '                      {/* Style fit */}'
traits_comment = '                      {/* Traits — all of them, wraps as needed */}'
contract_comment = '                      {/* Contract: years + risk + expires_on + market pills */}'
actions_comment = '                      {/* Actions (last column) */}'

formation_start = squad.find(formation_comment)
style_start = squad.find(style_comment, formation_start + 1) if formation_start >= 0 else -1
if formation_start >= 0 and style_start >= 0:
    block = squad[formation_start:style_start]
    squad = squad[:formation_start] + "                      {false && (<>\n" + block + "                      </>)}\n" + squad[style_start:]

style_start = squad.find(style_comment)
traits_start = squad.find(traits_comment, style_start + 1) if style_start >= 0 else -1
if style_start >= 0 and traits_start >= 0:
    block = squad[style_start:traits_start]
    squad = squad[:style_start] + "                      {false && (<>\n" + block + "                      </>)}\n" + squad[traits_start:]

contract_start = squad.find(contract_comment)
actions_start = squad.find(actions_comment, contract_start + 1) if contract_start >= 0 else -1
if contract_start >= 0 and actions_start >= 0:
    block = squad[contract_start:actions_start]
    squad = squad[:contract_start] + "                      {false && (<>\n" + block + "                      </>)}\n" + squad[actions_start:]

# Tabela mais compacta no celular: menos altura e menos largura por linha/célula.
squad = squad.replace('className="flex flex-col gap-4"', 'className="flex flex-col gap-2"', 1)
squad = squad.replace('className="w-full text-left border-collapse"', 'className="w-full table-auto text-left text-xs border-collapse"', 1)
squad = squad.replace('py-2.5 px-4', 'py-1 px-2')
squad = squad.replace('className="flex items-center gap-3"', 'className="flex items-center gap-2"')
squad = squad.replace(
    '<PlayerAvatar player={player} />',
    '<PlayerAvatar player={player} className="h-7 w-7 shrink-0 overflow-hidden rounded-md bg-gray-100 dark:bg-navy-700 flex items-center justify-center text-[10px] font-heading font-bold text-gray-500 dark:text-gray-300" />',
)
squad = squad.replace('font-semibold text-sm text-gray-900', 'font-semibold text-xs text-gray-900')
squad = squad.replace('text-sm font-medium text-gray-600', 'text-xs font-medium text-gray-600')
squad = squad.replace('text-sm text-gray-600 dark:text-gray-400 tabular-nums', 'text-xs text-gray-600 dark:text-gray-400 tabular-nums')
squad = squad.replace('text-sm text-gray-500 dark:text-gray-400 tabular-nums', 'text-xs text-gray-500 dark:text-gray-400 tabular-nums')
squad = squad.replace('className="py-1 px-2 w-28"', 'className="py-1 px-2 w-20"')
# TypeScript continua validando JSX oculto; mantem os mesmos guards com assertions explicitas.
squad = squad.replace('t(\`tactics.presetNames.\${currentPreset.id}\`, currentPreset.id)', 't(\`tactics.presetNames.\${currentPreset!.id}\`, currentPreset!.id)')
squad = squad.replace('injury={player.injury} />', 'injury={player.injury!} />')
squad = squad.replace(
    't(`tactics.presetNames.${currentPreset.id}`, currentPreset.id)',
    't(`tactics.presetNames.${currentPreset?.id ?? ""}`, currentPreset?.id ?? "")',
)

squad_path.write_text(squad, encoding="utf-8")



# Elenco: remove coluna Caracteristicas para reduzir a largura da tabela no mobile.
traits_header = '''                <th className="py-2.5 px-4 font-heading font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  {t("squad.traits")}
                </th>
'''
squad = squad.replace(traits_header, "", 1)
traits_cell = '''                      {/* Traits — all of them, wraps as needed */}
                      <td className="py-2.5 px-4">
                        <TraitList traits={player.traits || []} size="xs" />
                      </td>
'''
squad = squad.replace(traits_cell, "", 1)
squad_path.write_text(squad, encoding="utf-8")
print("CM mobile: coluna Caracteristicas removida do Elenco")

# Taticas mobile CM: compacta cabecalho, campo antes da lista e remove filtros visuais.
# Mantem toda a logica/engine existente; os ajustes abaixo sao apenas de apresentacao mobile.

# Botao MENU: fica alinhado ao bloco da data, ao lado de "dezembro", sem cobrir o titulo.
dashboard_path = root / "src" / "pages" / "Dashboard.tsx"
dashboard = dashboard_path.read_text(encoding="utf-8")
dashboard = dashboard.replace(
    'className="fixed left-3 top-3 z-30 flex h-12 w-12 items-center justify-center rounded-xl bg-navy-800 text-white shadow-lg ring-1 ring-white/10 active:scale-95"',
    'className="fixed left-3 top-12 z-30 flex h-12 w-12 items-center justify-center rounded-xl bg-navy-800 text-white shadow-lg ring-1 ring-white/10 active:scale-95"',
    1,
)
dashboard_path.write_text(dashboard, encoding="utf-8")

# Da mais respiro lateral ao titulo/data para o MENU nao ficar por cima do texto.
header_path = root / "src" / "components" / "dashboard" / "DashboardHeader.tsx"
header = header_path.read_text(encoding="utf-8")
header = header.replace(
    'className="flex min-w-0 items-center gap-2 pl-11 sm:gap-3 sm:pl-12"',
    'className="flex min-w-0 items-center gap-2 pl-16 sm:gap-3 sm:pl-12"',
    1,
)
header_path.write_text(header, encoding="utf-8")


# Cabecalho mobile: remove nome da aba e usa data em duas linhas.
dashboard_path = root / "src" / "pages" / "Dashboard.tsx"
dashboard = dashboard_path.read_text(encoding="utf-8")
dashboard = dashboard.replace('  formatDateFull,\n', '', 1)
dashboard = dashboard.replace(
    'const currentDate = formatDateFull(gameState.clock.current_date, settings.language);',
    '''const [cmYear, cmMonth, cmDay] = gameState.clock.current_date.slice(0, 10).split("-");
  const cmDateObject = new Date(Number(cmYear), Number(cmMonth) - 1, Number(cmDay), 12, 0, 0);
  const cmWeekday = new Intl.DateTimeFormat("pt-BR", { weekday: "long" }).format(cmDateObject);
  const cmMonths = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
  const currentDate = cmWeekday + "|" + cmDay + "/" + cmMonths[Number(cmMonth) - 1] + "/" + cmYear;''',
    1,
)
dashboard = dashboard.replace("  formatDateFull,\n", "", 1)
dashboard_path.write_text(dashboard, encoding="utf-8")

header_path = root / "src" / "components" / "dashboard" / "DashboardHeader.tsx"
header = header_path.read_text(encoding="utf-8")
header = header.replace(
    'className="text-xl font-heading font-bold uppercase tracking-wide text-gray-800 dark:text-gray-100"',
    'className="hidden text-xl font-heading font-bold uppercase tracking-wide text-gray-800 dark:text-gray-100 lg:block"',
    1,
)
old_date = '''          <p className="mt-0.5 flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
            <CalendarIcon className="h-3.5 w-3.5" />
            <span className="font-medium">{currentDate}</span>
          </p>
'''
new_date = '''          <p className="mt-0.5 flex flex-col items-start text-xs leading-tight text-gray-500 dark:text-gray-400">
            <span className="font-medium">{currentDate.split("|")[0]}</span>
            <span className="mt-0.5 font-semibold text-gray-700 dark:text-gray-300">
              {currentDate.split("|")[1]}
            </span>
          </p>
'''
header = header.replace(old_date, new_date, 1)
header_path.write_text(header, encoding="utf-8")
print("CM mobile: cabecalho sem nome da aba e data em duas linhas")

# Card superior de taticas: mantem a tatica ativa e as acoes, mas remove excesso visual.
command_path = root / "src" / "components" / "tactics" / "TacticsCommandBar.tsx"
command = command_path.read_text(encoding="utf-8")
command = command.replace('className="p-4 sm:p-5"', 'className="p-3 sm:p-4"', 1)
command = command.replace(
    'className="flex flex-col gap-4"',
    'className="flex flex-col gap-2"',
    1,
)
command = command.replace(
    'className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between"',
    'className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"',
    1,
)
sync_badge = '''                <Badge variant={isDirty ? "accent" : "neutral"} size="sm">
                  {isDirty ? t("tactics.unsavedChanges") : t("tactics.synced")}
                </Badge>
'''
command = command.replace(sync_badge, "", 1)
description = '''              <p className="mt-2 max-w-3xl text-sm text-gray-500 dark:text-gray-400">
                {activeTactic.description}
              </p>
'''
compact_summary = '''              <p className="mt-1 truncate text-base font-heading font-bold text-gray-900 dark:text-gray-100">
                {activeTactic.name}
              </p>
              <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                {formation} · {t(`common.playStyles.${activePlayStyle}`, activePlayStyle)}
              </p>
'''
command = command.replace(description, compact_summary, 1)

# Taticas: seletor compacto com todas as formacoes, sem reabrir o card grande.
formation_anchor = '''              <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                {formation} · {t(\`common.playStyles.\${activePlayStyle}\`, activePlayStyle)}
              </p>
'''
formation_controls = formation_anchor + '''              <div className="-mx-1 mt-2 flex gap-1 overflow-x-auto px-1 pb-1">
                {FORMATIONS.map((f) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => onFormationChange(f)}
                    className={formation === f
                      ? "shrink-0 rounded-md bg-primary-500 px-2.5 py-1.5 text-xs font-heading font-bold text-white"
                      : "shrink-0 rounded-md bg-gray-100 px-2.5 py-1.5 text-xs font-heading font-bold text-gray-600 dark:bg-navy-700 dark:text-gray-300"}
                  >
                    {f}
                  </button>
                ))}
              </div>
'''
command = command.replace(formation_anchor, formation_controls, 1)

command = command.replace(
    'className="grid gap-3 xl:grid-cols-[minmax(0,1.15fr)_minmax(18rem,0.85fr)_minmax(0,1.2fr)]"',
    'className="hidden grid gap-3 xl:grid-cols-[minmax(0,1.15fr)_minmax(18rem,0.85fr)_minmax(0,1.2fr)]"',
    1,
)
command = command.replace(
    'className="flex flex-wrap gap-2 xl:justify-end"',
    'className="flex flex-wrap gap-1.5 sm:justify-end"',
    1,
)
command_path.write_text(command, encoding="utf-8")

# Taticas: no mobile o campo aparece antes de Titulares/Banco.
tactics_path = root / "src" / "components" / "tactics" / "TacticsTab.tsx"
tactics = tactics_path.read_text(encoding="utf-8")
tactics = tactics.replace(
    'className="flex w-full flex-col gap-5"',
    'className="flex w-full flex-col gap-3"',
    1,
)
tactics = tactics.replace(
    'className="grid grid-cols-1 gap-5 xl:grid-cols-[260px_1fr_270px] xl:items-start"',
    'className="grid grid-cols-1 gap-3 xl:grid-cols-[1fr_260px_270px] xl:items-start"',
    1,
)
left_marker = '        {/* Left: player list */}'
center_marker = '        {/* Center: pitch */}'
right_marker = '        {/* Right: roles + phase blueprint */}'
left_start = tactics.find(left_marker)
center_start = tactics.find(center_marker, left_start + 1) if left_start >= 0 else -1
right_start = tactics.find(right_marker, center_start + 1) if center_start >= 0 else -1
if left_start >= 0 and center_start >= 0 and right_start >= 0:
    left_section = tactics[left_start:center_start]
    pitch_section = tactics[center_start:right_start]
    tactics = tactics[:left_start] + pitch_section + left_section + tactics[right_start:]
tactics_path.write_text(tactics, encoding="utf-8")

# Lista de jogadores na tatica: tira o card de filtro e deixa as linhas bem mais finas.
player_list_path = root / "src" / "components" / "tactics" / "TacticsPlayerList.tsx"
player_list = player_list_path.read_text(encoding="utf-8")
filters_block = '''      <TacticsFilters
        onClear={onClearFilters}
        onPlayerSearchChange={onPlayerSearchChange}
        onPositionFilterChange={onPositionFilterChange}
        playerSearch={playerSearch}
        positionFilter={positionFilter}
      />
'''
player_list = player_list.replace(
    filters_block,
    '      <div className="hidden">\n' + filters_block + '      </div>\n',
    1,
)
player_list = player_list.replace(
    'const rowClassName = `flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors ${',
    'const rowClassName = `flex w-full items-center gap-1.5 rounded-md px-2 py-0.5 text-left transition-colors ${',
    1,
)
player_list = player_list.replace(
    'className="min-w-0 flex-1 truncate text-sm font-medium text-gray-900 dark:text-gray-100"',
    'className="min-w-0 flex-1 truncate text-xs font-medium text-gray-900 dark:text-gray-100"',
)
player_list = player_list.replace(
    'className="flex flex-col gap-3"',
    'className="flex flex-col gap-2"',
    1,
)
player_list = player_list.replace(
    'className="border-b border-gray-100 px-3 py-2 dark:border-navy-700"',
    'className="border-b border-gray-100 px-2 py-1 dark:border-navy-700"',
)
player_list = player_list.replace(
    'className="p-1.5 space-y-0.5"',
    'className="space-y-0 p-1"',
)
player_list = player_list.replace(
    'className=`${rowClassName} flex-wrap gap-y-1`',
    'className=`${rowClassName} flex-wrap gap-y-0.5`',
    1,
)
player_list_path.write_text(player_list, encoding="utf-8")

# Campo: usa o campo real do jogo/engine; apenas reduz cabecalho, margens e altura no mobile.
pitch_path = root / "src" / "components" / "tactics" / "TacticsPitch.tsx"
pitch = pitch_path.read_text(encoding="utf-8")
pitch = pitch.replace(
    'className="flex flex-wrap items-center justify-between gap-3 rounded-t-xl border-b border-gray-100 bg-linear-to-r from-navy-700 to-navy-800 px-5 py-4 dark:border-navy-600"',
    'className="hidden"',
    1,
)
pitch = pitch.replace(
    'className="p-5 sm:p-6 lg:p-7"',
    'className="p-2 sm:p-3 lg:p-4"',
    1,
)
pitch_parent = 'className="relative mx-auto w-full max-w-[36rem] overflow-hidden rounded-[1.5rem] border border-primary-500/20 bg-linear-to-b from-primary-500 to-primary-700 shadow-inner"'
pitch_parent_repl = 'className="relative mx-auto w-full max-w-[36rem] overflow-hidden rounded-xl border border-primary-500/20 bg-linear-to-b from-primary-500 to-primary-700 shadow-inner"'
pitch = pitch.replace(pitch_parent, pitch_parent_repl, 1)
pitch = pitch.replace(
    '          <div className="aspect-[8/10] min-h-[35rem] w-full">',
    '''          <span className="absolute right-2 top-2 z-30 rounded-lg bg-navy-900/85 px-2 py-1 text-xs font-heading font-bold text-white shadow">
            {formation}
          </span>
          <div className="aspect-[8/10] min-h-[26rem] w-full sm:min-h-[32rem]">''',
    1,
)
pitch = pitch.replace('flex w-[6rem]', 'flex w-[4.75rem]', 1)
pitch = pitch.replace('h-[4.5rem] w-[4.5rem]', 'h-[3.75rem] w-[3.75rem]')
pitch = pitch.replace('flex w-[4.5rem]', 'flex w-[3.75rem]')
pitch_path.write_text(pitch, encoding="utf-8")

print("CM mobile: ajustes de Taticas e MENU aplicados")



# Partida mobile: layout de uma coluna sem cortes
# Mantem a engine, eventos e comandos intactos; altera somente apresentacao responsiva.
match_layout_path = root / "src" / "components" / "match" / "MatchScreenLayout.tsx"
match_layout = match_layout_path.read_text(encoding="utf-8")
match_layout = match_layout.replace(
    '"relative mx-auto w-full px-6"',
    '"relative mx-auto w-full px-2 sm:px-6"',
    1,
)
match_layout = match_layout.replace(
    '"absolute right-6 top-4"',
    '"absolute right-2 top-2 sm:right-6 sm:top-4"',
    1,
)
match_layout_path.write_text(match_layout, encoding="utf-8")

match_live_path = root / "src" / "components" / "match" / "MatchLive.tsx"
match_live = match_live_path.read_text(encoding="utf-8")
match_live = match_live.replace(
    'headerContentClassName="max-w-7xl py-3"',
    'headerContentClassName="max-w-7xl py-2 sm:py-3"',
    1,
)
match_live = match_live.replace(
    '<div className="flex items-center justify-between gap-4">\n            {/* Live indicator */}',
    '<div className="flex min-w-0 items-center justify-between gap-1 sm:gap-4">\n            {/* Live indicator */}',
    1,
)
match_live = match_live.replace(
    '            <div className="flex items-center gap-2">\n              {isRunning && (',
    '            <div className="hidden items-center gap-2 sm:flex">\n              {isRunning && (',
    1,
)
match_live = match_live.replace(
    '            <div className="flex items-center gap-6">\n              <div className="flex items-center gap-3">',
    '            <div className="flex min-w-0 flex-1 items-center justify-center gap-1 sm:flex-none sm:gap-6">\n              <div className="flex min-w-0 items-center gap-1 sm:gap-3">',
    1,
)
match_live = match_live.replace(
    'className="font-heading font-bold text-sm uppercase tracking-wider text-gray-800 dark:text-gray-200"',
    'className="max-w-[4.5rem] truncate text-[10px] font-heading font-bold uppercase tracking-wide text-gray-800 dark:text-gray-200 sm:max-w-none sm:text-sm sm:tracking-wider"',
)
match_live = match_live.replace(
    'className="text-xs text-gray-500 dark:text-gray-400"',
    'className="hidden text-xs text-gray-500 dark:text-gray-400 sm:block"',
    2,
)
match_live = match_live.replace(
    'className="w-10 h-10 rounded-lg flex items-center justify-center font-heading font-bold text-sm overflow-hidden"',
    'className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-lg text-sm font-heading font-bold sm:h-10 sm:w-10"',
)
match_live = match_live.replace(
    'imageClassName="h-8 w-8 object-contain drop-shadow"',
    'imageClassName="h-6 w-6 object-contain drop-shadow sm:h-8 sm:w-8"',
)
match_live = match_live.replace(
    'className="text-4xl font-heading font-bold text-gray-900 dark:text-white tabular-nums"',
    'className="text-3xl font-heading font-bold text-gray-900 dark:text-white tabular-nums sm:text-4xl"',
)
match_live = match_live.replace(
    '              <div className="flex items-center gap-3">\n                <TeamLogo\n                  team={awayFullTeam',
    '              <div className="flex min-w-0 items-center gap-1 sm:gap-3">\n                <TeamLogo\n                  team={awayFullTeam',
    1,
)
match_live = match_live.replace(
    '            <div className="flex items-center gap-2">\n              <Clock className="w-4 h-4 text-gray-500 dark:text-gray-400" />',
    '            <div className="hidden items-center gap-2 sm:flex">\n              <Clock className="w-4 h-4 text-gray-500 dark:text-gray-400" />',
    1,
)
match_live = match_live.replace(
    '<div className="flex-1 flex overflow-hidden">',
    '<div className="flex min-w-0 flex-1 flex-col overflow-x-hidden lg:flex-row">',
    1,
)
match_live = match_live.replace(
    '<div className="flex-1 flex flex-col">\n          <div className="flex bg-white',
    '<div className="flex min-w-0 flex-1 flex-col">\n          <div className="flex w-full bg-white',
    1,
)
match_live = match_live.replace(
    '<div className="flex-1 overflow-auto p-4">',
    '<div className="flex-1 overflow-auto p-2 sm:p-4">',
    1,
)
match_live = match_live.replace(
    '<aside className="w-72 bg-white dark:bg-navy-800 border-l border-gray-200 dark:border-navy-700 flex flex-col transition-colors duration-300">',
    '<aside className="flex w-full shrink-0 flex-col border-t border-gray-200 bg-white transition-colors duration-300 dark:border-navy-700 dark:bg-navy-800 lg:w-72 lg:border-l lg:border-t-0">',
    1,
)
match_live = match_live.replace(
    '<div className="p-4 border-b border-gray-200 dark:border-navy-700">',
    '<div className="border-b border-gray-200 p-3 dark:border-navy-700 sm:p-4">',
    1,
)
match_live = match_live.replace(
    '<div className="p-4 border-b border-gray-200 dark:border-navy-700 flex flex-col gap-2">',
    '<div className="flex flex-col gap-2 border-b border-gray-200 p-3 dark:border-navy-700 sm:p-4">',
    1,
)
match_live = match_live.replace(
    '<div className="p-4 flex-1 overflow-auto">',
    '<div className="flex-1 overflow-auto p-3 sm:p-4">',
    1,
)
match_live_path.write_text(match_live, encoding="utf-8")

# Intervalo/prelecao: no celular deixa de usar 3 colunas estreitas.
halftime_path = root / "src" / "components" / "match" / "HalfTimeBreak.tsx"
halftime = halftime_path.read_text(encoding="utf-8")
halftime = halftime.replace(
    'border-b border-gray-200 dark:border-navy-700 px-4 py-4 transition-colors duration-300',
    'border-b border-gray-200 px-2 py-3 transition-colors duration-300 dark:border-navy-700 sm:px-4 sm:py-4',
    1,
)
halftime = halftime.replace(
    '<div className="relative">\n          <div className="absolute right-0 top-0 flex items-center gap-3">',
    '<div className="flex flex-col gap-3 sm:relative">\n          <div className="order-2 flex items-center justify-center gap-2 sm:absolute sm:right-0 sm:top-0 sm:gap-3">',
    1,
)
halftime = halftime.replace(
    'className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r',
    'className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r sm:px-6 sm:py-2.5',
    1,
)
halftime = halftime.replace(
    '<div className="flex items-center justify-center gap-8">',
    '<div className="order-1 flex min-w-0 items-center justify-between gap-1 sm:justify-center sm:gap-8">',
    1,
)
halftime = halftime.replace(
    '<div className="flex items-center gap-3">\n              <TeamLogo',
    '<div className="flex min-w-0 items-center gap-1 sm:gap-3">\n              <TeamLogo',
    1,
)
halftime = halftime.replace(
    '<div className="flex items-center gap-3">\n              <p className="font-heading font-bold text-gray-800 dark:text-gray-200">',
    '<div className="flex min-w-0 items-center gap-1 sm:gap-3">\n              <p className="max-w-[4.5rem] truncate text-[10px] font-heading font-bold text-gray-800 dark:text-gray-200 sm:max-w-none sm:text-base">',
    1,
)
halftime = halftime.replace(
    '<p className="font-heading font-bold text-gray-800 dark:text-gray-200">\n                {snapshot.home_team.name}',
    '<p className="max-w-[4.5rem] truncate text-[10px] font-heading font-bold text-gray-800 dark:text-gray-200 sm:max-w-none sm:text-base">\n                {snapshot.home_team.name}',
    1,
)
halftime = halftime.replace(
    'className="w-12 h-12 rounded-xl flex items-center justify-center font-heading font-bold overflow-hidden"',
    'className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-xl font-heading font-bold sm:h-12 sm:w-12"',
)
halftime = halftime.replace(
    'imageClassName="h-9 w-9 object-contain drop-shadow"',
    'imageClassName="h-7 w-7 object-contain drop-shadow sm:h-9 sm:w-9"',
)
halftime = halftime.replace(
    'className="text-5xl font-heading font-bold text-gray-900 dark:text-white tabular-nums"',
    'className="text-3xl font-heading font-bold text-gray-900 dark:text-white tabular-nums sm:text-5xl"',
)
halftime = halftime.replace(
    '<div className="max-w-md mx-auto mt-3">',
    '<div className="order-3 mx-auto mt-1 w-full max-w-md sm:mt-3">',
    1,
)
halftime = halftime.replace(
    '<div className="px-6 py-6 grid grid-cols-3 gap-6">',
    '<div className="grid grid-cols-1 gap-3 px-3 py-3 lg:grid-cols-3 lg:gap-6 lg:px-6 lg:py-6">',
    1,
)
halftime_path.write_text(halftime, encoding="utf-8")

# Escalacoes: empilham no celular e nao estouram a largura.
match_panels_path = root / "src" / "components" / "match" / "MatchPanels.tsx"
match_panels = match_panels_path.read_text(encoding="utf-8")
match_panels = match_panels.replace(
    '<div className="flex gap-6">',
    '<div className="flex flex-col gap-4 sm:flex-row sm:gap-6">',
    1,
)
match_panels = match_panels.replace(
    '<div className="w-px bg-gray-200 dark:bg-navy-700 transition-colors duration-300" />',
    '<div className="hidden w-px bg-gray-200 transition-colors duration-300 dark:bg-navy-700 sm:block" />',
    1,
)
match_panels_path.write_text(match_panels, encoding="utf-8")

print("CM mobile: partida ao vivo, intervalo, estatisticas e escalacoes responsivas aplicadas")

# Validacao forte do pacote WFE
# Garante que o build realmente contem os ajustes solicitados. Se algum replace falhar,
# a compilacao para aqui em vez de gerar um APK aparentemente "novo" sem as mudancas.
checks = [
    (
        root / "src" / "pages" / "MainMenu.tsx",
        'src="/wfe-logo.svg"',
        "identidade WFE aplicada",
    ),
    (
        root / "src" / "pages" / "Dashboard.tsx",
        'top-12',
        "MENU reposicionado",
    ),
    (
        root / "src" / "components" / "dashboard" / "DashboardHeader.tsx",
        'pl-16',
        "cabecalho mobile corrigido",
    ),
    (
        root / "src" / "components" / "tactics" / "TacticsCommandBar.tsx",
        'className="hidden grid gap-3',
        "card de configuracoes de taticas compactado",
    ),
    (
        root / "src" / "components" / "tactics" / "TacticsTab.tsx",
        'xl:grid-cols-[1fr_260px_270px]',
        "campo antes da lista de jogadores",
    ),
    (
        root / "src" / "components" / "tactics" / "TacticsPlayerList.tsx",
        'rounded-md px-2 py-0.5',
        "linhas de titulares/banco compactas",
    ),
    (
        root / "src" / "components" / "tactics" / "TacticsPlayerList.tsx",
        '<div className="hidden">\n      <TacticsFilters',
        "filtro de taticas removido visualmente",
    ),
    (
        root / "src" / "components" / "tactics" / "TacticsPitch.tsx",
        'min-h-[26rem]',
        "campo de taticas compacto",
    ),
    (
        root / "src" / "components" / "squad" / "SquadRosterView.tsx",
        'table-auto text-left text-xs',
        "elenco compacto",
    ),
    (
        root / "src" / "components" / "match" / "MatchLive.tsx",
        'flex min-w-0 flex-1 flex-col overflow-x-hidden lg:flex-row',
        "partida ao vivo sem corte lateral",
    ),
    (
        root / "src" / "components" / "match" / "HalfTimeBreak.tsx",
        'grid grid-cols-1 gap-3 px-3 py-3 lg:grid-cols-3',
        "intervalo e prelecao em coluna no mobile",
    ),
    (
        root / "src" / "components" / "match" / "MatchPanels.tsx",
        'flex flex-col gap-4 sm:flex-row sm:gap-6',
        "escalacoes responsivas",
    ),
    (
        root / "src" / "components" / "dashboard" / "DashboardHeader.tsx",
        'currentDate.split("|")[1]',
        "data mobile em duas linhas",
    ),
    (
        root / "src" / "components" / "tactics" / "TacticsCommandBar.tsx",
        'FORMATIONS.map((f)',
        "todas as formacoes disponiveis na Tatica",
    ),
]
for path, needle, label in checks:
    generated = path.read_text(encoding="utf-8")
    if needle not in generated:
        raise RuntimeError(f"CM Teste 3: ajuste ausente no build: {label}")

print("WFE validado: ajustes visuais confirmados antes do build")
