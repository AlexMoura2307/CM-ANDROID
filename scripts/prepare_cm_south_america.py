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
scope_panel_path.write_text(r'''import { useTranslation } from "react-i18next";

import type { LeagueData, WorldRegionData } from "../store/gameStore";
import { countryName } from "../lib/countries";
import { competitionDisplayName } from "../lib/competitionName";
import { buildRegionLabel } from "../lib/teamRegions";
import { Badge, Card, CardBody, Checkbox } from "../components/ui";
import { Check, ChevronDown, ChevronRight, Globe2, Trophy } from "lucide-react";
import {
  competitionKindLabel,
  competitionRequiredRegions,
  competitionScopeLabel,
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
  const compName = (competition: LeagueData) => competitionDisplayName(competition, t);
  const selectedRegion = regions.find((region) => region.id === selectedHomeRegionId);

  return (
    <Card>
      <button
        type="button"
        onClick={onToggleScopeExpanded}
        className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left"
      >
        <span className="font-heading text-sm font-bold uppercase tracking-wide text-gray-700 dark:text-gray-200">
          {t("teamSelect.simulationScope")}
        </span>
        <span className="flex items-center gap-2">
          {!scopeExpanded && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {selectedCountryCode
                ? countryName(selectedCountryCode, i18n.language)
                : selectedRegion
                  ? buildRegionLabel(t, selectedRegion.id, selectedRegion.name)
                  : t("teamSelect.allCountries")}
            </span>
          )}
          <ChevronRight
            className={\`h-4 w-4 text-gray-400 transition-transform \${
              scopeExpanded ? "rotate-90" : ""
            }\`}
          />
        </span>
      </button>

      {scopeExpanded && (
        <CardBody className="space-y-4 pt-1">
          <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5 text-sm dark:border-navy-600 dark:bg-navy-800">
            <Globe2 className="h-4 w-4 text-primary-500" />
            <span className="text-xs font-heading font-bold uppercase tracking-[0.15em] text-gray-500 dark:text-gray-400">
              {t("teamSelect.homeRegion")}
            </span>
            <span className="ml-auto font-medium text-gray-800 dark:text-gray-100">
              {selectedRegion
                ? buildRegionLabel(t, selectedRegion.id, selectedRegion.name)
                : t("teamSelect.allCountries")}
            </span>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="text-xs font-heading font-bold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                {t("teamSelect.homeCountry")} · {t("teamSelect.simulatedCompetitions")}
              </p>
              <span className="text-[11px] text-gray-400">
                {regionCountries.length} países
              </span>
            </div>

            <div className="max-h-[25rem] overflow-y-auto rounded-xl border border-gray-200 dark:border-navy-600">
              {regionCountries.map((countryCode) => {
                const selected = countryCode === selectedCountryCode;
                return (
                  <div
                    key={countryCode}
                    className="border-b border-gray-200 last:border-b-0 dark:border-navy-600"
                  >
                    <button
                      type="button"
                      onClick={() => onSelectCountry(countryCode)}
                      className={\`flex w-full items-center gap-3 px-4 py-3 text-left transition-colors \${
                        selected
                          ? "bg-primary-500/10 text-primary-700 dark:bg-primary-500/15 dark:text-primary-300"
                          : "bg-white text-gray-800 hover:bg-gray-50 dark:bg-navy-800 dark:text-gray-100 dark:hover:bg-navy-700"
                      }\`}
                    >
                      <span
                        className={\`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border \${
                          selected
                            ? "border-primary-500 bg-primary-500 text-white"
                            : "border-gray-300 dark:border-navy-500"
                        }\`}
                      >
                        {selected ? <Check className="h-3.5 w-3.5" /> : null}
                      </span>
                      <span className="flex-1 font-heading text-sm font-bold uppercase tracking-wide">
                        {countryName(countryCode, i18n.language)}
                      </span>
                      {selected ? (
                        <ChevronDown className="h-4 w-4 text-primary-500" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-gray-400" />
                      )}
                    </button>

                    {selected && (
                      <div className="space-y-1 bg-gray-50 p-2 pl-5 dark:bg-navy-900/45">
                        {availableCompetitions.length === 0 ? (
                          <p className="px-3 py-3 text-xs text-gray-500 dark:text-gray-400">
                            Nenhuma competição cadastrada para este país.
                          </p>
                        ) : (
                          availableCompetitions.map((competition) => {
                            const enabled =
                              Boolean(competitionSelection[competition.id]) ||
                              mandatoryCompetitionIds.has(competition.id);
                            const isLocked = mandatoryCompetitionIds.has(competition.id);
                            const requiredRegions = competitionRequiredRegions(competition);
                            const missingRegions = requiredRegions.filter(
                              (regionId) => !activeRegionIds.includes(regionId),
                            );

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
                                className={\`rounded-lg border px-3 py-2.5 text-sm transition-colors \${
                                  enabled
                                    ? "border-primary-500/30 bg-white dark:bg-navy-800"
                                    : "border-gray-200 bg-gray-100 opacity-70 dark:border-navy-600 dark:bg-navy-800/70"
                                } \${
                                  !isLocked ? "cursor-pointer" : ""
                                }\`}
                              >
                                <div className="flex items-center justify-between gap-3">
                                  <span className="flex min-w-0 items-center gap-2">
                                    <Trophy className="h-4 w-4 shrink-0 text-accent-500" />
                                    <span className="truncate font-medium">
                                      {compName(competition)}
                                    </span>
                                  </span>
                                  <span
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

                                <div className="mt-2 flex flex-wrap gap-2">
                                  {competitionScopeLabel(t, competition.scope) && (
                                    <Badge variant="neutral" size="sm">
                                      {competitionScopeLabel(t, competition.scope)}
                                    </Badge>
                                  )}
                                  {competition.kind &&
                                    competition.kind !== "League" &&
                                    competitionKindLabel(t, competition.kind) && (
                                      <Badge variant="accent" size="sm">
                                        {competitionKindLabel(t, competition.kind)}
                                      </Badge>
                                    )}
                                  {isLocked && (
                                    <Badge variant="primary" size="sm">
                                      {t("teamSelect.yourClubBadge")}
                                    </Badge>
                                  )}
                                </div>

                                {missingRegions.length > 0 && (
                                  <p className="mt-2 text-[11px] text-amber-600 dark:text-amber-400">
                                    {t("teamSelect.requiresRegions", {
                                      regions: missingRegions
                                        .map((regionId) => buildRegionLabel(t, regionId))
                                        .join(", "),
                                    })}
                                  </p>
                                )}
                              </div>
                            );
                          })
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </CardBody>
      )}
    </Card>
  );
}
''', encoding="utf-8")

scope_panel_fixed = scope_panel_path.read_text(encoding="utf-8")
scope_panel_fixed = scope_panel_fixed.replace("\\`", "`").replace("\\${", "${")
scope_panel_path.write_text(scope_panel_fixed, encoding="utf-8")

print("FM-style country and competition list applied")


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
