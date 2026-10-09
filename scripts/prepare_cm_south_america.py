from pathlib import Path
import json

root = Path("upstream")

# Final CM mobile identity for the South America integrated test build.
conf_path = root / "src-tauri" / "tauri.conf.json"
conf = json.loads(conf_path.read_text(encoding="utf-8"))
conf["productName"] = "CM Teste 6"
conf["identifier"] = "com.cm.clubemanager.test6"
conf.setdefault("app", {}).setdefault("windows", [{}])[0]["title"] = "CM Teste 6"

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


# FM-style country/competition selector for the CM mobile team-selection flow.
# Domestic competitions now follow the selected country instead of showing every
# South American competition at once.
use_team_selection_path = root / "src" / "pages" / "useTeamSelection.ts"
use_team_selection = use_team_selection_path.read_text(encoding="utf-8")
old_competition_filter = """  const homeRegionTeamIds = new Set(
    (gameState?.teams ?? [])
      .filter((team) => regionCountries.includes(team.country))
      .map((team) => team.id),
  );

  const availableCompetitions = competitions.filter((competition) => {
    if (!selectedHomeRegionId) {
      return true;
    }

    const requiredRegions = competitionRequiredRegions(competition);
    return (
      requiredRegions.includes(selectedHomeRegionId) ||
      competition.region_id === selectedHomeRegionId ||
      (competition.country_id ? regionCountries.includes(competition.country_id) : false) ||
      competition.participant_ids?.some((teamId) => homeRegionTeamIds.has(teamId)) ||
      competition.scope === "Continental" ||
      competition.scope === "International"
    );
  });
"""
new_competition_filter = """  const homeRegionTeamIds = new Set(
    (gameState?.teams ?? [])
      .filter((team) => regionCountries.includes(team.country))
      .map((team) => team.id),
  );

  const selectedCountryTeamIds = new Set(
    (gameState?.teams ?? [])
      .filter((team) => !selectedCountryCode || team.country === selectedCountryCode)
      .map((team) => team.id),
  );

  const availableCompetitions = competitions.filter((competition) => {
    if (selectedCountryCode) {
      const hasCountryParticipant = Boolean(
        competition.participant_ids?.some((teamId) => selectedCountryTeamIds.has(teamId)),
      );
      if (competition.scope === "Domestic") {
        return competition.country_id === selectedCountryCode || hasCountryParticipant;
      }
      return hasCountryParticipant;
    }

    if (!selectedHomeRegionId) {
      return true;
    }

    const requiredRegions = competitionRequiredRegions(competition);
    return (
      requiredRegions.includes(selectedHomeRegionId) ||
      competition.region_id === selectedHomeRegionId ||
      (competition.country_id ? regionCountries.includes(competition.country_id) : false) ||
      competition.participant_ids?.some((teamId) => homeRegionTeamIds.has(teamId)) ||
      competition.scope === "Continental" ||
      competition.scope === "International"
    );
  });
"""
if old_competition_filter not in use_team_selection:
    raise RuntimeError("Team selection competition filter marker not found")
use_team_selection = use_team_selection.replace(
    old_competition_filter,
    new_competition_filter,
    1,
)
use_team_selection_path.write_text(use_team_selection, encoding="utf-8")

scope_panel_path = root / "src" / "pages" / "TeamSelectionScopePanel.tsx"
scope_panel_path.write_text(r'''import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { LeagueData, WorldRegionData } from "../store/gameStore";
import { countryName } from "../lib/countries";
import { competitionDisplayName } from "../lib/competitionName";
import { buildRegionLabel } from "../lib/teamRegions";
import { Card, CardBody, Checkbox } from "../components/ui";
import { ChevronRight, Globe2, Trophy } from "lucide-react";
import {
  competitionKindLabel,
  competitionRequiredRegions,
} from "./TeamSelection.helpers";

interface TeamSelectionScopePanelProps {
  scopeExpanded: boolean;
  onToggleScopeExpanded: () => void;
  regions: WorldRegionData[];
  selectedHomeRegionId: string | null;
  onSelectHomeRegion: (regionId: string | null) => void;
  selectedCountryCode: string | null;
  onSelectCountry: (countryCode: string | null) => void;
  regionCountries: string[];
  regionSelection: Record<string, boolean>;
  onRegionToggle: (regionId: string) => void;
  availableCompetitions: LeagueData[];
  competitionSelection: Record<string, boolean>;
  mandatoryCompetitionIds: Set<string>;
  activeRegionIds: string[];
  onCompetitionToggle: (competition: LeagueData) => void;
}

type CompetitionFilter = "all" | "league" | "cup" | "other";

export default function TeamSelectionScopePanel({
  scopeExpanded,
  onToggleScopeExpanded,
  regions,
  selectedHomeRegionId,
  selectedCountryCode,
  onSelectCountry,
  regionCountries,
  availableCompetitions,
  competitionSelection,
  mandatoryCompetitionIds,
  activeRegionIds,
  onCompetitionToggle,
}: TeamSelectionScopePanelProps) {
  const { t, i18n } = useTranslation();
  const [competitionFilter, setCompetitionFilter] = useState<CompetitionFilter>("all");
  const compName = (competition: LeagueData) => competitionDisplayName(competition, t);
  const selectedRegion = regions.find((region) => region.id === selectedHomeRegionId);

  const filteredCompetitions = availableCompetitions.filter((competition) => {
    if (competitionFilter === "all") return true;
    if (competitionFilter === "league") return competition.kind === "League";
    if (competitionFilter === "cup") return competition.kind === "Cup";
    return competition.kind !== "League" && competition.kind !== "Cup";
  });

  const filterButton = (key: CompetitionFilter, label: string) => (
    <button
      type="button"
      onClick={() => setCompetitionFilter(key)}
      className={`min-w-0 flex-1 border-r border-navy-600 px-2 py-2.5 text-center text-xs font-semibold last:border-r-0 ${
        competitionFilter === key
          ? "bg-primary-600 text-white"
          : "bg-navy-800 text-gray-300 hover:bg-navy-700"
      }`}
    >
      {label}
    </button>
  );

  return (
    <Card className="overflow-hidden border-navy-600 bg-navy-950">
      <button
        type="button"
        onClick={onToggleScopeExpanded}
        className="flex w-full items-center justify-between gap-3 border-b border-navy-600 bg-navy-900 px-4 py-3 text-left"
      >
        <span className="flex min-w-0 items-center gap-2">
          <Trophy className="h-4 w-4 shrink-0 text-primary-400" />
          <span className="truncate font-heading text-sm font-bold uppercase tracking-wide text-white">
            Competições
          </span>
        </span>
        <span className="flex min-w-0 items-center gap-2">
          <span className="max-w-[11rem] truncate text-xs text-gray-400">
            {selectedCountryCode
              ? countryName(selectedCountryCode, i18n.language)
              : selectedRegion
                ? buildRegionLabel(t, selectedRegion.id, selectedRegion.name)
                : t("teamSelect.allCountries")}
          </span>
          <ChevronRight
            className={`h-4 w-4 shrink-0 text-gray-400 transition-transform ${
              scopeExpanded ? "rotate-90" : ""
            }`}
          />
        </span>
      </button>

      {scopeExpanded && (
        <CardBody className="space-y-3 bg-navy-950 p-3">
          <div className="flex items-center gap-2 border-b border-navy-600 pb-2">
            <Globe2 className="h-4 w-4 text-primary-400" />
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500">
                País
              </p>
              <p className="truncate text-sm font-semibold text-white">
                {selectedCountryCode
                  ? countryName(selectedCountryCode, i18n.language)
                  : "Selecione um país"}
              </p>
            </div>
          </div>

          <div className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1">
            {regionCountries.map((countryCode) => {
              const selected = countryCode === selectedCountryCode;
              return (
                <button
                  key={countryCode}
                  type="button"
                  onClick={() => {
                    onSelectCountry(countryCode);
                    setCompetitionFilter("all");
                  }}
                  className={`shrink-0 rounded-md border px-3 py-2 text-xs font-semibold transition-colors ${
                    selected
                      ? "border-primary-500 bg-primary-600 text-white"
                      : "border-navy-600 bg-navy-800 text-gray-300"
                  }`}
                >
                  {countryName(countryCode, i18n.language)}
                </button>
              );
            })}
          </div>

          <div className="flex overflow-hidden rounded-lg border border-navy-600">
            {filterButton("all", "Todas")}
            {filterButton("league", "Ligas")}
            {filterButton("cup", "Taças")}
            {filterButton("other", "Outras")}
          </div>

          <div className="overflow-hidden rounded-lg border border-navy-600 bg-navy-900">
            <div className="grid grid-cols-[minmax(0,1fr)_4.5rem_2.5rem] border-b border-navy-600 bg-navy-800 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-gray-500">
              <span>Nome</span>
              <span>Tipo</span>
              <span className="text-center">Ativa</span>
            </div>

            <div className="max-h-[26rem] overflow-y-auto">
              {!selectedCountryCode ? (
                <p className="px-4 py-6 text-center text-xs text-gray-400">
                  Selecione um país para ver suas competições.
                </p>
              ) : filteredCompetitions.length === 0 ? (
                <p className="px-4 py-6 text-center text-xs text-gray-400">
                  Nenhuma competição cadastrada neste filtro.
                </p>
              ) : (
                filteredCompetitions.map((competition) => {
                  const enabled =
                    Boolean(competitionSelection[competition.id]) ||
                    mandatoryCompetitionIds.has(competition.id);
                  const isLocked = mandatoryCompetitionIds.has(competition.id);
                  const requiredRegions = competitionRequiredRegions(competition);
                  const missingRegions = requiredRegions.filter(
                    (regionId) => !activeRegionIds.includes(regionId),
                  );
                  const typeLabel =
                    competition.kind === "League"
                      ? "Liga"
                      : competition.kind === "Cup"
                        ? "Taça"
                        : competitionKindLabel(t, competition.kind) || "Outra";

                  return (
                    <div
                      key={competition.id}
                      role="button"
                      aria-pressed={enabled}
                      aria-disabled={isLocked}
                      tabIndex={isLocked ? -1 : 0}
                      onClick={() => !isLocked && onCompetitionToggle(competition)}
                      onKeyDown={(event) => {
                        if (!isLocked && (event.key === "Enter" || event.key === " ")) {
                          event.preventDefault();
                          onCompetitionToggle(competition);
                        }
                      }}
                      className={`grid grid-cols-[minmax(0,1fr)_4.5rem_2.5rem] items-center border-b border-navy-700 px-3 py-2.5 last:border-b-0 ${
                        enabled ? "bg-primary-950/30" : "bg-navy-900"
                      } ${
                        !isLocked ? "cursor-pointer active:bg-navy-800" : ""
                      }`}
                    >
                      <div className="flex min-w-0 items-center gap-2">
                        <span
                          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md border ${
                            enabled
                              ? "border-primary-500/50 bg-primary-500/10"
                              : "border-navy-600 bg-navy-800"
                          }`}
                        >
                          <Trophy className={`h-3.5 w-3.5 ${enabled ? "text-primary-400" : "text-gray-500"}`} />
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-xs font-semibold text-gray-100">
                            {compName(competition)}
                          </p>
                          {missingRegions.length > 0 && (
                            <p className="truncate text-[9px] text-amber-400">
                              Requer região adicional
                            </p>
                          )}
                          {isLocked && (
                            <p className="text-[9px] font-semibold uppercase tracking-wide text-primary-400">
                              Clube atual
                            </p>
                          )}
                        </div>
                      </div>

                      <span className="truncate text-[11px] text-gray-400">
                        {typeLabel}
                      </span>

                      <span
                        className="flex justify-center"
                        onClick={(event) => event.stopPropagation()}
                        onKeyDown={(event) => event.stopPropagation()}
                      >
                        <Checkbox
                          checked={enabled}
                          disabled={isLocked}
                          onChange={() => onCompetitionToggle(competition)}
                          aria-label={compName(competition)}
                        />
                      </span>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <p className="px-1 text-[10px] leading-relaxed text-gray-500">
            A lista acompanha o país selecionado. Competições de outros países não são misturadas.
          </p>
        </CardBody>
      )}
    </Card>
  );
}
''', encoding="utf-8")

scope_panel_fixed = scope_panel_path.read_text(encoding="utf-8")
scope_panel_fixed = scope_panel_fixed.replace("\\`", "`").replace("\\${", "${")
scope_panel_path.write_text(scope_panel_fixed, encoding="utf-8")

print("FM14-style mobile country and competition list applied")





# FM14-style compact club list on mobile. Desktop keeps the richer card grid.
team_grid_path = root / "src" / "pages" / "TeamSelectionGrid.tsx"
team_grid_path.write_text(r'''import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { TeamData } from "../store/gameStore";
import { formatVal } from "../lib/helpers";
import { Badge, Card, CardBody, TeamLocation, TeamLogo } from "../components/ui";
import { Landmark, Star, Trophy, Users, ChevronRight } from "lucide-react";

interface TeamGroup {
  id: string;
  name: string;
  order: number;
  teams: TeamData[];
}

interface TeamSelectionGridProps {
  clubSearch: string;
  onClubSearchChange: (value: string) => void;
  filteredTeamsCount: number;
  teamGroups: TeamGroup[];
  selectedTeamId: string | null;
  onSelectTeam: (teamId: string) => void;
  getTeamAvgOvr: (teamId: string) => number;
  getTeamPlayerCount: (teamId: string) => number;
}

export default function TeamSelectionGrid({
  clubSearch,
  onClubSearchChange,
  filteredTeamsCount,
  teamGroups,
  selectedTeamId,
  onSelectTeam,
  getTeamAvgOvr,
  getTeamPlayerCount,
}: TeamSelectionGridProps) {
  const { t, i18n } = useTranslation();

  const getReputationLabel = (
    rep: number,
  ): {
    label: string;
    variant: "primary" | "accent" | "success" | "danger" | "neutral";
  } => {
    if (rep >= 750) return { label: t("teamSelect.repWorldClass"), variant: "accent" };
    if (rep >= 600) return { label: t("teamSelect.repStrong"), variant: "success" };
    if (rep >= 400) return { label: t("teamSelect.repAverage"), variant: "neutral" };
    return { label: t("teamSelect.repDeveloping"), variant: "danger" };
  };

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <input
          type="text"
          value={clubSearch}
          onChange={(event) => onClubSearchChange(event.target.value)}
          placeholder={t("teamSelect.searchClubs")}
          className="min-w-0 flex-1 rounded-lg border border-navy-600 bg-navy-800 px-3 py-2.5 text-sm text-gray-100 placeholder:text-gray-500 md:border-gray-200 md:bg-white md:text-gray-700 md:dark:border-navy-600 md:dark:bg-navy-800 md:dark:text-gray-200"
        />
        <span className="shrink-0 text-[11px] font-heading font-bold uppercase tracking-wider text-gray-500">
          {filteredTeamsCount}
        </span>
      </div>

      {filteredTeamsCount === 0 ? (
        <p className="py-10 text-center text-sm text-gray-500 dark:text-gray-400">
          {t("teamSelect.noClubsMatch")}
        </p>
      ) : (
        <>
          <div className="space-y-3 md:hidden">
            {teamGroups.map((group) => (
              <section key={group.id} className="overflow-hidden rounded-lg border border-navy-600 bg-navy-900">
                <div className="border-b border-navy-600 bg-navy-800 px-3 py-2">
                  <p className="truncate text-[10px] font-heading font-bold uppercase tracking-[0.18em] text-gray-400">
                    {group.name}
                  </p>
                </div>
                <div>
                  {group.teams.map((team) => {
                    const isSelected = selectedTeamId === team.id;
                    const avgOvr = getTeamAvgOvr(team.id);
                    const playerCount = getTeamPlayerCount(team.id);

                    return (
                      <button
                        key={team.id}
                        type="button"
                        onClick={() => onSelectTeam(team.id)}
                        className={`grid w-full grid-cols-[2.5rem_minmax(0,1fr)_3rem_1.75rem] items-center gap-2 border-b border-navy-700 px-3 py-2.5 text-left last:border-b-0 ${
                          isSelected ? "bg-primary-950/40" : "bg-navy-900 active:bg-navy-800"
                        }`}
                      >
                        <TeamLogo
                          team={team}
                          className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-md bg-white/10 text-xs font-bold text-gray-300"
                        />

                        <div className="min-w-0">
                          <p className={`truncate text-xs font-bold ${
                            isSelected ? "text-primary-300" : "text-gray-100"
                          }`}>
                            {team.name}
                          </p>
                          <TeamLocation
                            city={team.city}
                            countryCode={team.country}
                            locale={i18n.language}
                            className="mt-0.5 truncate text-[10px] text-gray-500"
                            iconClassName="w-2.5 h-2.5"
                            flagClassName="text-[10px] leading-none"
                          />
                          <p className="mt-0.5 text-[9px] text-gray-500">
                            {playerCount} jogadores
                          </p>
                        </div>

                        <div className="text-center">
                          <p className="text-[9px] uppercase tracking-wide text-gray-500">OVR</p>
                          <p className="font-heading text-sm font-bold text-primary-400">{avgOvr}</p>
                        </div>

                        <ChevronRight
                          className={`h-4 w-4 ${
                            isSelected ? "text-primary-400" : "text-gray-600"
                          }`}
                        />
                      </button>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>

          <div className="hidden max-h-[640px] space-y-5 overflow-y-auto pr-1 md:block">
            {teamGroups.map((group) => (
              <div key={group.id}>
                <p className="mb-2 text-xs font-heading font-bold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                  {group.name}
                </p>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  {group.teams.map((team) => {
                    const isSelected = selectedTeamId === team.id;
                    const avgOvr = getTeamAvgOvr(team.id);
                    const repInfo = getReputationLabel(team.reputation);
                    const playerCount = getTeamPlayerCount(team.id);

                    return (
                      <button
                        key={team.id}
                        type="button"
                        onClick={() => onSelectTeam(team.id)}
                        className={`rounded-xl text-left transition-all duration-200 ${
                          isSelected
                            ? "scale-[1.01] ring-2 ring-primary-500 ring-offset-2 dark:ring-offset-navy-900"
                            : "hover:scale-[1.01]"
                        }`}
                      >
                        <Card accent={isSelected ? "primary" : "none"} className="h-full">
                          <div
                            className={`rounded-t-xl p-4 ${
                              isSelected
                                ? "bg-gradient-to-r from-primary-600 to-primary-700"
                                : "bg-gradient-to-r from-navy-700 to-navy-800"
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <TeamLogo
                                  team={team}
                                  className={`flex h-12 w-12 items-center justify-center overflow-hidden rounded-lg font-heading text-lg font-bold ${
                                    isSelected
                                      ? "bg-white/20 text-white"
                                      : "bg-white/10 text-gray-300"
                                  }`}
                                />
                                <div>
                                  <h3 className="font-heading text-sm font-bold uppercase tracking-wide text-white">
                                    {team.name}
                                  </h3>
                                  <TeamLocation
                                    city={team.city}
                                    countryCode={team.country}
                                    locale={i18n.language}
                                    className="mt-0.5 text-xs text-gray-300"
                                    iconClassName="w-3 h-3"
                                    flagClassName="text-xs leading-none"
                                  />
                                </div>
                              </div>
                              {isSelected && (
                                <Star className="h-5 w-5 fill-current text-accent-400" />
                              )}
                            </div>
                          </div>

                          <CardBody className="p-4">
                            <div className="grid grid-cols-2 gap-3">
                              <InfoStat
                                icon={<Trophy className="h-3.5 w-3.5" />}
                                label={t("teamSelect.reputation")}
                                value={
                                  <Badge variant={repInfo.variant} size="sm">
                                    {repInfo.label}
                                  </Badge>
                                }
                              />
                              <InfoStat
                                icon={<Users className="h-3.5 w-3.5" />}
                                label={t("teamSelect.squad")}
                                value={
                                  <span className="font-heading font-bold text-gray-800 dark:text-gray-200">
                                    {playerCount}
                                  </span>
                                }
                              />
                              <InfoStat
                                icon={<Landmark className="h-3.5 w-3.5" />}
                                label={t("teamSelect.finances")}
                                value={
                                  <span className="font-heading font-bold text-gray-800 dark:text-gray-200">
                                    {formatVal(team.finance)}
                                  </span>
                                }
                              />
                              <InfoStat
                                icon={<Star className="h-3.5 w-3.5" />}
                                label={t("teamSelect.avgOvr")}
                                value={
                                  <span className="font-heading text-lg font-bold text-primary-500">
                                    {avgOvr}
                                  </span>
                                }
                              />
                            </div>
                          </CardBody>
                        </Card>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function InfoStat({ icon, label, value }: { icon: ReactNode; label: string; value: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
        {icon} {label}
      </span>
      {value}
    </div>
  );
}
''', encoding="utf-8")

team_grid_fixed = team_grid_path.read_text(encoding="utf-8")
team_grid_fixed = team_grid_fixed.replace("\\`", "`").replace("\\${", "${")
team_grid_path.write_text(team_grid_fixed, encoding="utf-8")

print("FM14-style mobile club selection list applied")

# Compact the full team-selection shell for true portrait-phone use.
team_selection_path = root / "src" / "pages" / "TeamSelection.tsx"
team_selection = team_selection_path.read_text(encoding="utf-8")
replacements = [
    (
        'className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4 shadow-sm dark:border-navy-700 dark:bg-navy-800"',
        'className="sticky top-0 z-20 flex items-center justify-between border-b border-gray-200 bg-white px-3 py-3 shadow-sm dark:border-navy-700 dark:bg-navy-800 md:px-6 md:py-4"',
    ),
    (
        'className="flex items-center gap-4"',
        'className="flex min-w-0 items-center gap-2 md:gap-4"',
    ),
    (
        'className="font-heading text-xl font-bold uppercase tracking-wide text-gray-800 dark:text-gray-100"',
        'className="truncate font-heading text-base font-bold uppercase tracking-wide text-gray-800 dark:text-gray-100 md:text-xl"',
    ),
    (
        'className="mt-0.5 text-xs text-gray-500 dark:text-gray-400"',
        'className="mt-0.5 hidden text-xs text-gray-500 dark:text-gray-400 md:block"',
    ),
    (
        'className="flex items-center gap-3"',
        'className="flex shrink-0 items-center gap-1.5 md:gap-3"',
    ),
    (
        'className={`flex items-center gap-2 rounded-lg bg-gradient-to-r from-primary-500 to-primary-600 px-6 py-2.5 font-heading text-sm font-bold uppercase tracking-wider text-white shadow-md transition-all hover:from-primary-600 hover:to-primary-700 hover:shadow-lg hover:shadow-primary-500/20 ${',
        'className={`flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-primary-500 to-primary-600 px-3 py-2 font-heading text-[11px] font-bold uppercase tracking-wide text-white shadow-md transition-all hover:from-primary-600 hover:to-primary-700 hover:shadow-lg hover:shadow-primary-500/20 md:gap-2 md:px-6 md:py-2.5 md:text-sm md:tracking-wider ${',
    ),
    (
        'className="space-y-5 p-6"',
        'className="space-y-3 p-3 pb-6 md:space-y-5 md:p-6"',
    ),
    (
        'className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.8fr)]"',
        'className="grid gap-3 md:gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.8fr)]"',
    ),
]
for old, new in replacements:
    if old not in team_selection:
        raise RuntimeError(f"TeamSelection mobile marker not found: {old[:70]}")
    team_selection = team_selection.replace(old, new, 1)
team_selection_path.write_text(team_selection, encoding="utf-8")

sidebar_path = root / "src" / "pages" / "TeamSelectionSidebar.tsx"
sidebar = sidebar_path.read_text(encoding="utf-8")
sidebar = sidebar.replace(
    '    <Card accent="accent" className="h-fit">',
    '    <Card accent="accent" className="h-fit overflow-hidden">',
    1,
)
sidebar = sidebar.replace(
    '      <CardBody className="space-y-5 p-5">',
    '      <CardBody className="space-y-3 p-3 md:space-y-5 md:p-5">',
    1,
)
sidebar = sidebar.replace(
    'className="mt-1 font-heading text-2xl font-bold text-gray-900 dark:text-white"',
    'className="mt-1 truncate font-heading text-lg font-bold text-gray-900 dark:text-white md:text-2xl"',
    1,
)
sidebar = sidebar.replace(
    'className="grid grid-cols-2 gap-3"',
    'className="grid grid-cols-4 gap-2 md:grid-cols-2 md:gap-3"',
    1,
)
sidebar = sidebar.replace(
    'className="space-y-2"',
    'className="grid grid-cols-1 gap-1.5 md:space-y-2"',
    1,
)
sidebar_path.write_text(sidebar, encoding="utf-8")

print("CM mobile team-selection shell compacted")

# Mundo > Clubes: compact FM-style list on phones, richer cards on desktop.
teams_list_path = root / "src" / "components" / "teams" / "TeamsListTab.tsx"
teams_list = teams_list_path.read_text(encoding="utf-8")

old_grid = '''                      {leagueOpen && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pl-2">
                          {league.teams.map((card) => (
                            <TeamCardView
                              key={card.team.id}
                              card={card}
                              isUser={card.team.id === userTeamId}
                              language={i18n.language}
                              t={t}
                              onSelect={onSelectTeam}
                            />
                          ))}
                        </div>
                      )}'''

new_grid = '''                      {leagueOpen && (
                        <div className="pl-2">
                          <div className="overflow-hidden rounded-lg border border-navy-600 md:hidden">
                            <div className="grid grid-cols-[2.5rem_minmax(0,1fr)_3rem_1.75rem] items-center gap-2 border-b border-navy-600 bg-navy-800 px-3 py-2 text-[9px] font-bold uppercase tracking-wider text-gray-500">
                              <span />
                              <span>Clube</span>
                              <span className="text-center">OVR</span>
                              <span />
                            </div>
                            {league.teams.map((card) => (
                              <MobileTeamRow
                                key={card.team.id}
                                card={card}
                                isUser={card.team.id === userTeamId}
                                language={i18n.language}
                                t={t}
                                onSelect={onSelectTeam}
                              />
                            ))}
                          </div>

                          <div className="hidden grid-cols-1 gap-3 md:grid md:grid-cols-2">
                            {league.teams.map((card) => (
                              <TeamCardView
                                key={card.team.id}
                                card={card}
                                isUser={card.team.id === userTeamId}
                                language={i18n.language}
                                t={t}
                                onSelect={onSelectTeam}
                              />
                            ))}
                          </div>
                        </div>
                      )}'''

if old_grid not in teams_list:
    raise RuntimeError("TeamsListTab grid marker not found")
teams_list = teams_list.replace(old_grid, new_grid, 1)

mobile_component = r'''
function MobileTeamRow({
  card,
  isUser,
  language,
  t,
  onSelect,
}: {
  card: TeamCard;
  isUser: boolean;
  language: string;
  t: ReturnType<typeof useTranslation>["t"];
  onSelect: (id: string) => void;
}) {
  const { team, roster_size: rosterSize, avg_ovr: avgOvr, league_pos: leaguePos } = card;

  return (
    <button
      type="button"
      onClick={() => onSelect(team.id)}
      className={`grid w-full grid-cols-[2.5rem_minmax(0,1fr)_3rem_1.75rem] items-center gap-2 border-b border-navy-700 px-3 py-2.5 text-left last:border-b-0 ${
        isUser ? "bg-primary-950/35" : "bg-navy-900 active:bg-navy-800"
      }`}
    >
      <TeamLogo
        team={team}
        className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-md border border-white/10 bg-white/10 text-xs font-bold text-gray-300"
        imageClassName="h-8 w-8 object-contain"
      />

      <div className="min-w-0">
        <div className="flex min-w-0 items-center gap-1.5">
          <p className={`truncate text-xs font-bold ${isUser ? "text-primary-300" : "text-gray-100"}`}>
            {team.name}
          </p>
          {isUser && (
            <span className="shrink-0 rounded bg-primary-500/20 px-1 py-0.5 text-[8px] font-bold uppercase text-primary-300">
              {t("teams.yourTeam")}
            </span>
          )}
        </div>
        <TeamLocation
          city={team.city}
          countryCode={team.country}
          locale={language}
          className="mt-0.5 truncate text-[10px] text-gray-500"
          iconClassName="h-2.5 w-2.5"
          flagClassName="text-[10px] leading-none"
        />
        <p className="mt-0.5 text-[9px] text-gray-500">
          {rosterSize} jogadores{leaguePos > 0 ? ` · #${leaguePos}` : ""}
        </p>
      </div>

      <div className="text-center">
        <p className="text-[9px] uppercase tracking-wide text-gray-500">OVR</p>
        <p className="font-heading text-sm font-bold text-primary-400">{avgOvr}</p>
      </div>

      <ChevronRight className="h-4 w-4 text-gray-600" />
    </button>
  );
}

'''

insert_marker = 'function TeamCardView({'
if insert_marker not in teams_list:
    raise RuntimeError("TeamCardView marker not found")
teams_list = teams_list.replace(insert_marker, mobile_component + insert_marker, 1)
teams_list_path.write_text(teams_list, encoding="utf-8")

print("CM Mundo clubes mobile compact list applied")

# Mundo > Competições: compact FM14-style list on phones, keeping desktop behaviour.
competitions_overview_path = root / "src" / "components" / "tournaments" / "CompetitionsOverview.tsx"
competitions_overview_path.write_text(r'''import { useTranslation } from "react-i18next";
import { ChevronRight, Trophy, Users } from "lucide-react";
import type { LeagueData } from "../../store/types";
import { getCompetitiveFixtures } from "../../lib/fixtures";
import { competitionDisplayName } from "../../lib/competitionName";
import { Card, CardHeader, CardBody, Badge } from "../ui";

interface Props {
  competitions: LeagueData[];
  userTeamId: string | null;
  onSelect: (id: string) => void;
}

export type CompetitionScope = "Domestic" | "Regional" | "Continental" | "International";

export const SCOPE_ORDER: CompetitionScope[] = [
  "Domestic",
  "Regional",
  "Continental",
  "International",
];

export function getCompetitionStatus(comp: LeagueData): "notStarted" | "inProgress" | "completed" {
  const competitive = getCompetitiveFixtures(comp.fixtures);
  if (competitive.length === 0) return "notStarted";
  let completed = 0;
  for (const f of competitive) {
    if (f.status === "Completed") completed++;
  }
  if (completed === 0) return "notStarted";
  if (completed >= competitive.length) return "completed";
  return "inProgress";
}

export default function CompetitionsOverview({ competitions, userTeamId, onSelect }: Props) {
  const { t } = useTranslation();

  if (competitions.length === 0) {
    return (
      <Card>
        <CardBody>
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <Trophy className="h-8 w-8 text-gray-300 dark:text-navy-600" />
            <p className="text-sm text-gray-500 dark:text-gray-400">{t("tournaments.noActive")}</p>
          </div>
        </CardBody>
      </Card>
    );
  }

  const grouped = new Map<CompetitionScope, LeagueData[]>();
  for (const c of competitions) {
    const scope = (c.scope as CompetitionScope | undefined) ?? "Domestic";
    const bucket = grouped.get(scope);
    if (bucket) bucket.push(c);
    else grouped.set(scope, [c]);
  }
  const byScope = SCOPE_ORDER.filter((s) => grouped.has(s)).map(
    (s) => [s, grouped.get(s)!] as const,
  );

  const statusLabel = (status: "notStarted" | "inProgress" | "completed") =>
    status === "notStarted"
      ? t("tournaments.competitions.statusNotStarted")
      : status === "inProgress"
        ? t("tournaments.competitions.statusInProgress")
        : t("tournaments.competitions.statusCompleted");

  return (
    <Card className="overflow-hidden">
      <CardHeader>{t("tournaments.competitions.title")}</CardHeader>
      <CardBody className="p-0">
        {byScope.map(([scope, comps]) => (
          <div key={scope}>
            <div className="border-b border-gray-100 bg-gray-50 px-3 py-2 dark:border-navy-600 dark:bg-navy-800 md:px-4">
              <h5 className="font-heading text-[10px] font-bold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-300 md:text-xs md:tracking-wider">
                {t(`teamSelect.scopes.${scope}`)}
              </h5>
            </div>

            <div className="md:hidden">
              <div className="grid grid-cols-[minmax(0,1fr)_4rem_4.75rem_1.25rem] border-b border-navy-600 bg-navy-800 px-3 py-2 text-[9px] font-bold uppercase tracking-wider text-gray-500">
                <span>Nome</span>
                <span>Tipo</span>
                <span>Status</span>
                <span />
              </div>
              {comps.map((comp) => {
                const status = getCompetitionStatus(comp);
                const isParticipating =
                  userTeamId != null && (comp.participant_ids?.includes(userTeamId) ?? false);

                return (
                  <button
                    type="button"
                    key={comp.id}
                    onClick={() => onSelect(comp.id)}
                    className="grid w-full grid-cols-[minmax(0,1fr)_4rem_4.75rem_1.25rem] items-center border-b border-navy-700 bg-navy-900 px-3 py-2.5 text-left last:border-b-0 active:bg-navy-800"
                    data-testid={`competitions-overview-row-${comp.id}`}
                  >
                    <div className="min-w-0">
                      <p className="truncate text-xs font-semibold text-gray-100">
                        {competitionDisplayName(comp, t)}
                      </p>
                      <div className="mt-0.5 flex items-center gap-1.5">
                        <span className="text-[9px] text-gray-500">
                          {t("schedule.season", { number: comp.season })}
                        </span>
                        {isParticipating && (
                          <span className="inline-flex items-center gap-0.5 rounded bg-primary-500/15 px-1 py-0.5 text-[8px] font-bold uppercase text-primary-300">
                            <Users className="h-2.5 w-2.5" />
                            Seu clube
                          </span>
                        )}
                      </div>
                    </div>

                    <span className="truncate text-[10px] text-gray-400">
                      {t(`teamSelect.kinds.${comp.kind ?? "League"}`)}
                    </span>

                    <span
                      className={`truncate text-[9px] font-semibold ${
                        status === "completed"
                          ? "text-accent-400"
                          : status === "inProgress"
                            ? "text-primary-400"
                            : "text-gray-500"
                      }`}
                    >
                      {statusLabel(status)}
                    </span>

                    <ChevronRight className="h-4 w-4 text-gray-600" />
                  </button>
                );
              })}
            </div>

            <div className="hidden divide-y divide-gray-100 dark:divide-navy-600 md:block">
              {comps.map((comp) => {
                const status = getCompetitionStatus(comp);
                const isParticipating =
                  userTeamId != null && (comp.participant_ids?.includes(userTeamId) ?? false);

                return (
                  <button
                    type="button"
                    key={comp.id}
                    onClick={() => onSelect(comp.id)}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50 dark:hover:bg-navy-700"
                    data-testid={`competitions-overview-row-${comp.id}`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="truncate text-sm font-semibold text-gray-800 dark:text-gray-200">
                          {competitionDisplayName(comp, t)}
                        </span>
                        <Badge variant="neutral" size="sm">
                          {t(`teamSelect.kinds.${comp.kind ?? "League"}`)}
                        </Badge>
                        {isParticipating && (
                          <Badge variant="primary" size="sm">
                            <Users className="mr-0.5 inline h-3 w-3" />
                            {t("tournaments.competitions.participating")}
                          </Badge>
                        )}
                      </div>
                      <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">
                        {t("schedule.season", { number: comp.season })}
                      </p>
                    </div>
                    <Badge
                      variant={
                        status === "completed"
                          ? "accent"
                          : status === "inProgress"
                            ? "primary"
                            : "neutral"
                      }
                      size="sm"
                    >
                      {statusLabel(status)}
                    </Badge>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}
''', encoding="utf-8")

competitions_overview_fixed = competitions_overview_path.read_text(encoding="utf-8")
competitions_overview_fixed = competitions_overview_fixed.replace("\\`", "`").replace("\\${", "${")
competitions_overview_path.write_text(competitions_overview_fixed, encoding="utf-8")

print("CM Mundo competicoes mobile compact list applied")

# Mundo: compact the remaining card-heavy views for portrait phones without
# changing their data/actions. Desktop keeps the richer layouts.
mobile_tweaks = {
    root / "src" / "components" / "manager" / "ManagersWorldTab.tsx": [
        ('<div className="space-y-5">', '<div className="space-y-3 md:space-y-5">'),
        ('<CardBody className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">', '<CardBody className="flex flex-col gap-2 p-3 md:flex-row md:items-center md:justify-between md:p-5">'),
        ('className="text-2xl font-heading font-bold uppercase tracking-wide text-gray-900 dark:text-gray-100"', 'className="text-lg font-heading font-bold uppercase tracking-wide text-gray-900 dark:text-gray-100 md:text-2xl"'),
        ('<div className="grid grid-cols-1 gap-5 xl:grid-cols-2">', '<div className="grid grid-cols-1 gap-3 md:gap-5 xl:grid-cols-2">'),
        ('<CardBody className="space-y-4">', '<CardBody className="space-y-3 p-3 md:space-y-4 md:p-5">'),
        ('className="mt-1 text-left text-xl font-heading font-bold uppercase tracking-wide text-accent-500 transition-colors hover:text-accent-400"', 'className="mt-1 text-left text-base font-heading font-bold uppercase tracking-wide text-accent-500 transition-colors hover:text-accent-400 md:text-xl"'),
        ('className="mt-2 text-left text-xl font-heading font-bold uppercase tracking-wide text-primary-500 transition-colors hover:text-primary-400"', 'className="mt-2 text-left text-base font-heading font-bold uppercase tracking-wide text-primary-500 transition-colors hover:text-primary-400 md:text-xl"'),
        ('className="mt-2 text-xl font-heading font-bold uppercase tracking-wide text-gray-700 dark:text-gray-200"', 'className="mt-2 text-base font-heading font-bold uppercase tracking-wide text-gray-700 dark:text-gray-200 md:text-xl"'),
        ('className="grid grid-cols-3 gap-3 text-sm"', 'className="grid grid-cols-3 gap-2 text-sm md:gap-3"'),
        ('className="rounded-lg bg-gray-50 p-3 dark:bg-navy-800/70"', 'className="rounded-lg bg-gray-50 p-2 dark:bg-navy-800/70 md:p-3"'),
        ('className="text-lg font-heading font-bold text-gray-800 dark:text-gray-100"', 'className="text-base font-heading font-bold text-gray-800 dark:text-gray-100 md:text-lg"'),
    ],
    root / "src" / "components" / "transfers" / "TransferCentreWorldTab.tsx": [
        ('<div className="space-y-5">', '<div className="space-y-3 md:space-y-5">'),
        ('<CardBody className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">', '<CardBody className="flex flex-col gap-2 p-3 md:flex-row md:items-center md:justify-between md:p-5">'),
        ('className="text-2xl font-heading font-bold uppercase tracking-wide text-gray-900 dark:text-gray-100"', 'className="text-lg font-heading font-bold uppercase tracking-wide text-gray-900 dark:text-gray-100 md:text-2xl"'),
        ('<div className="grid grid-cols-1 gap-5 xl:grid-cols-2">', '<div className="grid grid-cols-1 gap-3 md:gap-5 xl:grid-cols-2">'),
        ('<CardBody className="space-y-4">', '<CardBody className="space-y-2 p-3 md:space-y-4 md:p-5">'),
        ('className="rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-navy-600 dark:bg-navy-800/70"', 'className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-navy-600 dark:bg-navy-800/70 md:rounded-xl md:p-4"'),
        ('className="text-left text-xl font-heading font-bold uppercase tracking-wide text-primary-500 transition-colors hover:text-primary-400"', 'className="text-left text-base font-heading font-bold uppercase tracking-wide text-primary-500 transition-colors hover:text-primary-400 md:text-xl"'),
        ('className="text-left text-xl font-heading font-bold uppercase tracking-wide text-accent-500 transition-colors hover:text-accent-400"', 'className="text-left text-base font-heading font-bold uppercase tracking-wide text-accent-500 transition-colors hover:text-accent-400 md:text-xl"'),
        ('className="mt-4 grid grid-cols-2 gap-3 text-sm"', 'className="mt-3 grid grid-cols-2 gap-2 text-sm md:mt-4 md:gap-3"'),
        ('className="rounded-lg bg-white p-3 dark:bg-navy-700/70"', 'className="rounded-lg bg-white p-2 dark:bg-navy-700/70 md:p-3"'),
        ('className="text-lg font-heading font-bold text-gray-800 dark:text-gray-100"', 'className="text-base font-heading font-bold text-gray-800 dark:text-gray-100 md:text-lg"'),
    ],
    root / "src" / "components" / "hallOfFame" / "HallOfFameWorldTab.tsx": [
        ('<div className="space-y-5">', '<div className="space-y-3 md:space-y-5">'),
        ('<CardBody className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">', '<CardBody className="flex flex-col gap-3 p-3 md:flex-row md:items-center md:justify-between md:p-5">'),
        ('className="text-2xl font-heading font-bold uppercase tracking-wide text-gray-900 dark:text-gray-100"', 'className="text-lg font-heading font-bold uppercase tracking-wide text-gray-900 dark:text-gray-100 md:text-2xl"'),
        ('<section className="space-y-4">', '<section className="space-y-3 md:space-y-4">'),
        ('className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"', 'className="grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-4 xl:grid-cols-3"'),
        ('className="grid grid-cols-1 gap-5 xl:grid-cols-2"', 'className="grid grid-cols-1 gap-3 md:gap-5 xl:grid-cols-2"'),
        ('className="grid grid-cols-1 gap-4 xl:grid-cols-2"', 'className="grid grid-cols-1 gap-3 md:gap-4 xl:grid-cols-2"'),
        ('<CardBody className="space-y-4">', '<CardBody className="space-y-3 p-3 md:space-y-4 md:p-5">'),
        ('className="mt-2 text-xl font-heading font-bold uppercase tracking-wide text-gray-900 dark:text-gray-100"', 'className="mt-2 text-base font-heading font-bold uppercase tracking-wide text-gray-900 dark:text-gray-100 md:text-xl"'),
        ('className="mt-1 text-left text-xl font-heading font-bold uppercase tracking-wide text-accent-500 transition-colors hover:text-accent-400"', 'className="mt-1 text-left text-base font-heading font-bold uppercase tracking-wide text-accent-500 transition-colors hover:text-accent-400 md:text-xl"'),
        ('className="rounded-lg bg-gray-50 p-3 dark:bg-navy-800/70"', 'className="rounded-lg bg-gray-50 p-2 dark:bg-navy-800/70 md:p-3"'),
        ('className="text-lg font-heading font-bold text-gray-800 dark:text-gray-100"', 'className="text-base font-heading font-bold text-gray-800 dark:text-gray-100 md:text-lg"'),
    ],
}

for path, pairs in mobile_tweaks.items():
    content = path.read_text(encoding="utf-8")
    for old, new in pairs:
        if old in content:
            content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")

print("CM Mundo mobile consistency sweep applied")

# Mundo > Jogadores: compact filters and the wide table on portrait phones.
players_list_path = root / "src" / "components" / "players" / "PlayersListTab.tsx"
players_list = players_list_path.read_text(encoding="utf-8")

for old, new in [
    (
        '      <div className="flex flex-wrap gap-3 mb-4 items-center">',
        '      <div className="mb-3 flex flex-col gap-2 md:mb-4 md:flex-row md:flex-wrap md:items-center md:gap-3">',
    ),
    (
        '        <div className="relative flex-1 min-w-[200px] max-w-sm">',
        '        <div className="relative w-full md:min-w-[200px] md:max-w-sm md:flex-1">',
    ),
    (
        '          className="min-w-44 font-heading font-bold uppercase tracking-wider"',
        '          className="w-full font-heading font-bold uppercase tracking-wider md:w-auto md:min-w-44"',
    ),
    (
        '          <div className="overflow-x-auto">',
        '          <div className="overflow-x-hidden md:overflow-x-auto">',
    ),
    (
        '            <table className="w-full text-left border-collapse">',
        '            <table className="w-full table-fixed border-collapse text-left max-md:[&_th]:px-2 max-md:[&_td]:px-2 max-md:[&_th:nth-child(4)]:hidden max-md:[&_td:nth-child(4)]:hidden max-md:[&_th:nth-child(5)]:hidden max-md:[&_td:nth-child(5)]:hidden max-md:[&_th:nth-child(6)]:hidden max-md:[&_td:nth-child(6)]:hidden max-md:[&_th:nth-child(8)]:hidden max-md:[&_td:nth-child(8)]:hidden md:table-auto">',
    ),
    (
        '            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 dark:border-navy-600">',
        '            <div className="flex items-center justify-between gap-2 border-t border-gray-100 px-2 py-2.5 dark:border-navy-600 md:px-4 md:py-3">',
    ),
]:
    if old in players_list:
        players_list = players_list.replace(old, new, 1)

players_list = players_list.replace(
    '        <div className="flex gap-1.5">',
    '        <div className="flex w-full gap-1.5 overflow-x-auto pb-0.5 md:w-auto md:overflow-visible md:pb-0">',
    2,
)

name_cell_old = '''                      <td className="py-2.5 px-4">
                        <div className="flex items-center gap-3">
                          <PlayerAvatar player={summary} />
                          <span className="font-semibold text-sm text-gray-800 dark:text-gray-200 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                            {summary.match_name}
                          </span>
                        </div>
                      </td>'''
name_cell_new = '''                      <td className="min-w-0 px-2 py-2.5 md:px-4">
                        <div className="flex min-w-0 items-center gap-2 md:gap-3">
                          <PlayerAvatar player={summary} />
                          <div className="min-w-0">
                            <span className="block truncate text-sm font-semibold text-gray-800 transition-colors group-hover:text-primary-600 dark:text-gray-200 dark:group-hover:text-primary-400">
                              {summary.match_name}
                            </span>
                            <span className="mt-0.5 block truncate text-[10px] text-gray-500 md:hidden">
                              {summary.team_name ?? t("common.freeAgent")}
                            </span>
                          </div>
                        </div>
                      </td>'''
if name_cell_old in players_list:
    players_list = players_list.replace(name_cell_old, name_cell_new, 1)

players_list = players_list.replace(
    '                      <td className="py-2.5 px-4 text-sm text-gray-600 dark:text-gray-400 tabular-nums">',
    '                      <td className="w-10 px-1 py-2.5 text-center text-xs tabular-nums text-gray-600 dark:text-gray-400 md:w-auto md:px-4 md:text-left md:text-sm">',
    1,
)

players_list_path.write_text(players_list, encoding="utf-8")
print("CM Mundo jogadores mobile compact table applied")







# CM diagnostic: stage initial save writes so real-device save failures are
# reproducible in CI against the same consolidated South America package.
game_persistence_path = root / "src-tauri" / "crates" / "db" / "src" / "game_persistence.rs"
game_persistence = game_persistence_path.read_text(encoding="utf-8")

write_game_and_stats_old = """    pub fn write_game_and_stats(
        db: &GameDatabase,
        game: &Game,
        stats: &StatsState,
        save_id: &str,
        save_name: &str,
    ) -> Result<(), String> {
        let transaction = db
            .conn()
            .unchecked_transaction()
            .map_err(|_| game_persistence_write_error())?;
        write_game_to_connection(&transaction, game, save_id, save_name)?;
        stats_repo::replace_stats_state(&transaction, stats)?;
        transaction
            .commit()
            .map_err(|_| game_persistence_write_error())?;
        Ok(())
    }
"""
write_game_and_stats_new = """    pub fn write_game_and_stats(
        db: &GameDatabase,
        game: &Game,
        stats: &StatsState,
        save_id: &str,
        save_name: &str,
    ) -> Result<(), String> {
        let transaction = db
            .conn()
            .unchecked_transaction()
            .map_err(|_| "be.error.gamePersistence.writeFailed?stage=transactionOpen".to_string())?;
        write_game_to_connection(&transaction, game, save_id, save_name)?;
        stats_repo::replace_stats_state(&transaction, stats)
            .map_err(|_| "be.error.gamePersistence.writeFailed?stage=stats".to_string())?;
        transaction
            .commit()
            .map_err(|_| "be.error.gamePersistence.writeFailed?stage=commit".to_string())?;
        Ok(())
    }
"""
if write_game_and_stats_old in game_persistence:
    game_persistence = game_persistence.replace(
        write_game_and_stats_old,
        write_game_and_stats_new,
        1,
    )

meta_end_old = """        },
    )?;

    for manager in &managers {
        manager_repo::upsert_manager(conn, manager)?;
    }
"""
meta_end_new = """        },
    )
    .map_err(|_| "be.error.gamePersistence.writeFailed?stage=meta".to_string())?;

    for manager in &managers {
        manager_repo::upsert_manager(conn, manager)
            .map_err(|_| "be.error.gamePersistence.writeFailed?stage=managers".to_string())?;
    }
"""
if meta_end_old in game_persistence:
    game_persistence = game_persistence.replace(meta_end_old, meta_end_new, 1)
stage_replacements = {
    "    meta_repo::upsert_meta(": "    meta_repo::upsert_meta(",
}
# Wrap the major persistence stages with a stage parameter while preserving
# the existing backend translation key.
for old, new in [
    ("    team_repo::upsert_teams(conn, &game.teams)?;",
     '    team_repo::upsert_teams(conn, &game.teams).map_err(|_| "be.error.gamePersistence.writeFailed?stage=teams".to_string())?;'),
    ("    journal_repo::persist_cash_journal(conn, game)?;",
     '    journal_repo::persist_cash_journal(conn, game).map_err(|_| "be.error.gamePersistence.writeFailed?stage=journal".to_string())?;'),
    ("    player_repo::upsert_players(conn, &game.players)?;",
     '    player_repo::upsert_players(conn, &game.players).map_err(|_| "be.error.gamePersistence.writeFailed?stage=players".to_string())?;'),
    ("    staff_repo::replace_staff_list(conn, &game.staff)?;",
     '    staff_repo::replace_staff_list(conn, &game.staff).map_err(|_| "be.error.gamePersistence.writeFailed?stage=staff".to_string())?;'),
    ("    message_repo::replace_messages(conn, &game.messages)?;",
     '    message_repo::replace_messages(conn, &game.messages).map_err(|_| "be.error.gamePersistence.writeFailed?stage=messages".to_string())?;'),
    ("    news_repo::replace_news_list(conn, &game.news)?;",
     '    news_repo::replace_news_list(conn, &game.news).map_err(|_| "be.error.gamePersistence.writeFailed?stage=news".to_string())?;'),
    ("        league_repo::upsert_league(conn, league)?;",
     '        league_repo::upsert_league(conn, league).map_err(|_| "be.error.gamePersistence.writeFailed?stage=league".to_string())?;'),
    ("    competition_repo::replace_competitions(conn, &game.competitions)?;",
     '    competition_repo::replace_competitions(conn, &game.competitions).map_err(|_| "be.error.gamePersistence.writeFailed?stage=competitions".to_string())?;'),
    ("    national_team_repo::replace_national_teams(conn, &game.national_teams)?;",
     '    national_team_repo::replace_national_teams(conn, &game.national_teams).map_err(|_| "be.error.gamePersistence.writeFailed?stage=nationalTeams".to_string())?;'),
    ("    objective_repo::upsert_objectives(conn, &objective_rows)?;",
     '    objective_repo::upsert_objectives(conn, &objective_rows).map_err(|_| "be.error.gamePersistence.writeFailed?stage=objectives".to_string())?;'),
    ("    scouting_repo::upsert_scouting_list(conn, &scouting_rows)?;",
     '    scouting_repo::upsert_scouting_list(conn, &scouting_rows).map_err(|_| "be.error.gamePersistence.writeFailed?stage=scouting".to_string())?;'),
    ("    scouting_repo::upsert_youth_scouting_list(conn, &youth_scouting_rows)?;",
     '    scouting_repo::upsert_youth_scouting_list(conn, &youth_scouting_rows).map_err(|_| "be.error.gamePersistence.writeFailed?stage=youthScouting".to_string())?;'),
]:
    if old in game_persistence:
        game_persistence = game_persistence.replace(old, new, 1)
game_persistence_path.write_text(game_persistence, encoding="utf-8")

game_mod_path = root / "src-tauri" / "src" / "commands" / "game" / "mod.rs"
game_mod = game_mod_path.read_text(encoding="utf-8")
diagnostic_test = r'''
#[cfg(test)]
mod cm_south_america_save_qa {
    use super::*;
    use db::save_manager::SaveManager;
    use ofm_core::career::{begin_career, CareerScope};

    #[test]
    fn consolidated_south_america_can_select_a_brazilian_club_and_create_first_save() {
        let Ok(ofm_path) = std::env::var("CM_TEST_OFM") else {
            return;
        };
        let package_id = "cm-south-america-2026";
        let unique = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
            .to_string();
        let root = std::env::temp_dir().join(format!("cm-save-qa-{unique}"));
        let packages_dir = root.join("packages");
        let saves_dir = root.join("saves");
        std::fs::create_dir_all(&packages_dir).unwrap();
        std::fs::create_dir_all(&saves_dir).unwrap();
        std::fs::copy(
            &ofm_path,
            packages_dir.join(format!("{package_id}.ofm")),
        )
        .unwrap();

        let startup_options = normalize_startup_options(None).unwrap();
        let opening_year = u32::try_from(startup_options.start_year).ok();
        let (mut world, package_lockfile) = load_world_data_from_package_ids(
            &packages_dir,
            &[package_id.to_string()],
            opening_year,
            None,
            &ofm_core::generator::DefinitionSources::embedded_only(),
        )
        .expect("South America OFM loads");

        let clock = game_clock_for_world(&startup_options, &world.metadata).unwrap();
        let opening_year = u32::try_from(clock.start_date.year())
            .unwrap_or_else(|_| ofm_core::generator::default_opening_year());
        ofm_core::generator::normalize_imported_world_for_career_start(&mut world, opening_year);

        let manager = Manager::new(
            "mgr_user".to_string(),
            "CM".to_string(),
            "QA".to_string(),
            "1980-01-01".to_string(),
            "BR".to_string(),
        );
        let brazil_team_id = world
            .teams
            .iter()
            .find(|team| matches!(team.country.as_str(), "BR" | "BRA"))
            .or_else(|| world.teams.iter().find(|team| {
                let name = team.name.to_lowercase();
                name.contains("são paulo") || name.contains("sao paulo")
            }))
            .or_else(|| world.teams.first())
            .expect("world has a team")
            .id
            .clone();

        let (mut game, stats) = build_game_from_world_data(
            clock,
            manager,
            &startup_options,
            world,
        );
        game.package_lockfile = package_lockfile;

        let stats = begin_career(
            &mut game,
            &brazil_team_id,
            CareerScope::default(),
            stats,
        )
        .expect("Brazilian career begins");

        let mut save_manager = SaveManager::init(&saves_dir).unwrap();
        let save_id = create_new_save(
            &mut save_manager,
            &game,
            &stats,
            "CM South America QA",
        )
        .unwrap_or_else(|error| panic!("initial CM save failed: {error}"));

        assert!(!save_id.is_empty());
        let loaded = save_manager.load_game(&save_id).expect("saved career reloads");
        assert_eq!(loaded.manager.team_id.as_deref(), Some(brazil_team_id.as_str()));
        assert_eq!(loaded.teams.len(), game.teams.len());
        assert_eq!(loaded.players.len(), game.players.len());

        let _ = std::fs::remove_dir_all(root);
    }
}
'''
if "mod cm_south_america_save_qa" not in game_mod:
    game_mod += "\n" + diagnostic_test
game_mod_path.write_text(game_mod, encoding="utf-8")

print("CM South America first-save QA instrumentation applied")


# Fast DB-only regression for the real South America package. This avoids
# compiling the desktop Tauri shell just to find a SQLite persistence failure.
db_lib_path = root / "src-tauri" / "crates" / "db" / "src" / "lib.rs"
db_lib = db_lib_path.read_text(encoding="utf-8")
db_fast_test = r'''
#[cfg(test)]
mod cm_full_package_persistence_fast {
    use chrono::{TimeZone, Utc};
    use domain::manager::Manager;
    use ofm_core::career::{begin_career, CareerScope};
    use ofm_core::clock::GameClock;
    use ofm_core::game::Game;
    use std::path::Path;

    #[test]
    fn real_south_america_package_can_create_and_reload_first_save() {
        let Ok(ofm_path) = std::env::var("CM_TEST_OFM") else {
            return;
        };

        let (package, errors) =
            ofm_core::generator::load_world_package_from_ofm(Path::new(&ofm_path));
        assert!(errors.is_empty(), "OFM load errors: {errors:?}");
        let mut world = ofm_core::generator::build_world_from_package(
            &package,
            Some(2026),
            &ofm_core::generator::DefinitionSources::embedded_only(),
        )
        .expect("world builds from real South America package");
        ofm_core::generator::normalize_imported_world_for_career_start(&mut world, 2026);

        let stats_state = world.stats.clone();
        let clock = GameClock::new(
            Utc.with_ymd_and_hms(2026, 7, 1, 12, 0, 0)
                .single()
                .expect("valid opening date"),
        );
        let manager = Manager::new(
            "mgr_cm_qa".to_string(),
            "CM".to_string(),
            "QA".to_string(),
            "1980-01-01".to_string(),
            "BR".to_string(),
        );

        let brazil_team_id = world
            .teams
            .iter()
            .find(|team| team.country == "BR")
            .expect("Brazilian team exists")
            .id
            .clone();

        let mut game = Game::new(
            clock,
            manager,
            world.teams,
            world.players,
            world.staff,
            Vec::new(),
        );
        game.competitions = world.competitions;
        game.national_teams = world.national_teams;
        game.news = world.news;
        game.world_history = world.world_history;
        game.extra_translations = world.extra_translations;
        game.active_region_ids = world.default_active_regions;
        game.active_competition_ids = world.default_active_competitions;
        game.sync_legacy_league();

        let stats_state =
            begin_career(&mut game, &brazil_team_id, CareerScope::default(), stats_state)
                .expect("Brazilian career begins");

        let unique = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!("cm-db-fast-{unique}"));
        std::fs::create_dir_all(&root).unwrap();

        let mut saves = crate::save_manager::SaveManager::init(&root).expect("save manager");
        let save_id = saves
            .create_save_with_stats(&game, &stats_state, "CM Fast Save QA")
            .unwrap_or_else(|error| panic!("CM first save persistence failed: {error}"));

        let loaded = saves.load_game(&save_id).expect("first save reloads");
        assert_eq!(loaded.manager.team_id.as_deref(), Some(brazil_team_id.as_str()));
        assert_eq!(loaded.teams.len(), game.teams.len());
        assert_eq!(loaded.players.len(), game.players.len());

        std::fs::remove_dir_all(root).ok();
    }
}
'''
if "mod cm_full_package_persistence_fast" not in db_lib:
    db_lib += "\n" + db_fast_test
db_lib_path.write_text(db_lib, encoding="utf-8")
print("CM fast DB save regression applied")


# Preserve the reserve squad role through SQLite saves/reloads. Upstream's DB
# parser predates the Reserve enum variant and otherwise collapses it to Senior.
player_repo_path = root / "src-tauri" / "crates" / "db" / "src" / "repositories" / "player_repo.rs"
player_repo = player_repo_path.read_text(encoding="utf-8")
player_repo = player_repo.replace(
    '''fn parse_squad_role(s: &str) -> SquadRole {
    match s {
        "Youth" => SquadRole::Youth,
        _ => SquadRole::Senior,
    }
}''',
    '''fn parse_squad_role(s: &str) -> SquadRole {
    match s {
        "Youth" => SquadRole::Youth,
        "Reserve" => SquadRole::Reserve,
        _ => SquadRole::Senior,
    }
}''',
    1,
)
player_repo = player_repo.replace(
    '''R::Senior; [("Senior", R::Senior), ("Youth", R::Youth)]''',
    '''R::Senior; [
                    ("Senior", R::Senior),
                    ("Reserve", R::Reserve),
                    ("Youth", R::Youth)
                ]''',
    1,
)
player_repo = player_repo.replace(
    '''    .map_err(|_| GAME_PERSISTENCE_WRITE_ERROR.to_string())?;
    Ok(())
}

/// Insert or replace multiple players.''',
    '''    .map_err(|error| {
        eprintln!("[CM SAVE] player SQL write failed id={} error={:?}", p.id, error);
        GAME_PERSISTENCE_WRITE_ERROR.to_string()
    })?;
    Ok(())
}

/// Insert or replace multiple players.''',
    1,
)

player_repo = player_repo.replace(
    '''pub fn upsert_players(conn: &Connection, players: &[Player]) -> Result<(), String> {
    for p in players {
        upsert_player(conn, p)?;
    }
    Ok(())
}''',
    '''pub fn upsert_players(conn: &Connection, players: &[Player]) -> Result<(), String> {
    use std::collections::HashSet;

    let mut occupied_jerseys: HashSet<(String, u8)> = HashSet::new();
    let mut ordered: Vec<&Player> = players.iter().collect();

    // Keep the first-team shirt number when imported reserve/youth squads reuse
    // the same number under the parent club id. The DB schema requires a unique
    // (team_id, jersey_number) pair, while real reserve/base teams may reuse them.
    ordered.sort_by_key(|player| match player.squad_role {
        SquadRole::Senior => 0u8,
        SquadRole::Reserve => 1u8,
        SquadRole::Youth => 2u8,
    });

    for p in ordered {
        if let (Some(team_id), Some(jersey_number)) = (&p.team_id, p.jersey_number) {
            let key = (team_id.clone(), jersey_number);
            if !occupied_jerseys.insert(key) {
                let mut normalized = p.clone();
                normalized.jersey_number = None;
                upsert_player(conn, &normalized)?;
                continue;
            }
        }
        upsert_player(conn, p)?;
    }
    Ok(())
}''',
    1,
)
player_repo_path.write_text(player_repo, encoding="utf-8")
print("CM Reserve squad role persistence fixed")


# Persistence diagnostics + full South America save round-trip regression test.
game_persistence_path = root / "src-tauri" / "crates" / "db" / "src" / "game_persistence.rs"
game_persistence = game_persistence_path.read_text(encoding="utf-8")
stage_replacements = {
    "    meta_repo::upsert_meta(": "    log::info!(\"[cm-save] stage=meta\");\n    meta_repo::upsert_meta(",
    "    for manager in &managers {": "    log::info!(\"[cm-save] stage=managers count={}\", managers.len());\n    for manager in &managers {",
    "    team_repo::upsert_teams(conn, &game.teams)?;": "    log::info!(\"[cm-save] stage=teams count={}\", game.teams.len());\n    team_repo::upsert_teams(conn, &game.teams)?;",
    "    journal_repo::persist_cash_journal(conn, game)?;": "    log::info!(\"[cm-save] stage=cash_journal count={}\", game.cash_journal.len());\n    journal_repo::persist_cash_journal(conn, game)?;",
    "    player_repo::upsert_players(conn, &game.players)?;": "    log::info!(\"[cm-save] stage=players count={}\", game.players.len());\n    player_repo::upsert_players(conn, &game.players)?;",
    "    staff_repo::replace_staff_list(conn, &game.staff)?;": "    log::info!(\"[cm-save] stage=staff count={}\", game.staff.len());\n    staff_repo::replace_staff_list(conn, &game.staff)?;",
    "    message_repo::replace_messages(conn, &game.messages)?;": "    log::info!(\"[cm-save] stage=messages count={}\", game.messages.len());\n    message_repo::replace_messages(conn, &game.messages)?;",
    "    news_repo::replace_news_list(conn, &game.news)?;": "    log::info!(\"[cm-save] stage=news count={}\", game.news.len());\n    news_repo::replace_news_list(conn, &game.news)?;",
    "    competition_repo::replace_competitions(conn, &game.competitions)?;": "    log::info!(\"[cm-save] stage=competitions count={}\", game.competitions.len());\n    competition_repo::replace_competitions(conn, &game.competitions)?;",
    "    national_team_repo::replace_national_teams(conn, &game.national_teams)?;": "    log::info!(\"[cm-save] stage=national_teams count={}\", game.national_teams.len());\n    national_team_repo::replace_national_teams(conn, &game.national_teams)?;",
    "    objective_repo::upsert_objectives(conn, &objective_rows)?;": "    log::info!(\"[cm-save] stage=objectives count={}\", objective_rows.len());\n    objective_repo::upsert_objectives(conn, &objective_rows)?;",
    "    scouting_repo::upsert_scouting_list(conn, &scouting_rows)?;": "    log::info!(\"[cm-save] stage=scouting count={}\", scouting_rows.len());\n    scouting_repo::upsert_scouting_list(conn, &scouting_rows)?;",
    "    scouting_repo::upsert_youth_scouting_list(conn, &youth_scouting_rows)?;": "    log::info!(\"[cm-save] stage=youth_scouting count={}\", youth_scouting_rows.len());\n    scouting_repo::upsert_youth_scouting_list(conn, &youth_scouting_rows)?;",
}
for old, new in stage_replacements.items():
    if old in game_persistence and new not in game_persistence:
        game_persistence = game_persistence.replace(old, new, 1)
game_persistence_path.write_text(game_persistence, encoding="utf-8")

game_mod_path = root / "src-tauri" / "src" / "commands" / "game" / "mod.rs"
game_mod = game_mod_path.read_text(encoding="utf-8")
if "cm_south_america_full_save_roundtrip" not in game_mod:
    game_mod += r'''

#[cfg(test)]
mod cm_full_package_persistence_test {
    use super::*;
    use db::save_manager::SaveManager;
    use domain::manager::Manager;
    use std::path::Path;

    #[test]
    fn cm_south_america_full_save_roundtrip() {
        let Ok(ofm_path) = std::env::var("CM_TEST_OFM_PATH") else {
            eprintln!("CM_TEST_OFM_PATH not set; skipping external package persistence regression");
            return;
        };
        let path = Path::new(&ofm_path);
        assert!(path.exists(), "CM_TEST_OFM_PATH does not exist: {ofm_path}");

        let (package, errors) = ofm_core::generator::load_world_package_from_ofm(path);
        assert!(errors.is_empty(), "OFM load errors: {errors:?}");
        let sources = ofm_core::generator::DefinitionSources::embedded_only();
        let mut world =
            ofm_core::generator::build_world_from_package(&package, Some(2026), &sources)
                .expect("build South America world");
        ofm_core::generator::normalize_imported_world_for_career_start(&mut world, 2026);

        let startup_options = normalize_startup_options(None).expect("startup options");
        let clock = game_clock_for_world(&startup_options, &world.metadata).expect("game clock");
        let manager = Manager::new(
            "mgr_user".to_string(),
            "CM".to_string(),
            "Tester".to_string(),
            "1980-01-01".to_string(),
            "BR".to_string(),
        );
        let (mut game, stats_state) =
            build_game_from_world_data(clock, manager, &startup_options, world);
        let team_id = game
            .teams
            .first()
            .expect("South America package has at least one team")
            .id
            .clone();
        let stats_state =
            begin_career(&mut game, &team_id, CareerScope::default(), stats_state)
                .expect("begin career with full South America package");

        let unique = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let saves_dir =
            std::env::temp_dir().join(format!("cm-south-america-save-roundtrip-{unique}"));
        std::fs::create_dir_all(&saves_dir).unwrap();
        let mut manager = SaveManager::init(&saves_dir).expect("init SaveManager");
        let save_id = manager
            .create_save_with_stats(&game, &stats_state, "CM South America QA")
            .expect("persist full South America career after team selection");
        let loaded = manager.load_game(&save_id).expect("reload persisted CM career");
        assert_eq!(loaded.manager.team_id.as_deref(), Some(team_id.as_str()));
        assert_eq!(loaded.teams.len(), game.teams.len());
        assert_eq!(loaded.players.len(), game.players.len());
        let _ = std::fs::remove_dir_all(&saves_dir);
    }
}
'''
    game_mod_path.write_text(game_mod, encoding="utf-8")

print("CM full-package persistence regression instrumentation applied")
