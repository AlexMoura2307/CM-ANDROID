import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { type GameStateData, useGameStore } from "../../store/gameStore";
import type { PlayerSelectionOptions } from "../../store/gameStore";
import type { PlayerSquadRole } from "../../store/types";
import { useFetchedSquad } from "../../hooks/useFetchedSquad";
import { getPlayerSquadRole } from "../../lib/playerSquad";
import SquadRosterView from "./SquadRosterView";
import type { SquadListSortState } from "./SquadRosterView.state";

interface SquadTabProps {
  gameState: GameStateData | null;
  managerId: string;
  onSelectPlayer: (id: string, options?: PlayerSelectionOptions) => void;
  onGameUpdate?: (g: GameStateData) => void;
  sortState?: SquadListSortState;
  onSortStateChange?: (sortState: SquadListSortState) => void;
  initialView?: PlayerSquadRole;
}

const views: Array<{ id: PlayerSquadRole; label: string }> = [
  { id: "Senior", label: "Principal" },
  { id: "Reserve", label: "Reservas" },
  { id: "Youth", label: "Base" },
];

export default function SquadTab({
  gameState,
  managerId,
  onSelectPlayer,
  onGameUpdate,
  sortState,
  onSortStateChange,
  initialView = "Senior",
}: SquadTabProps) {
  const { t } = useTranslation();
  const { sessionState } = useGameStore();
  const [activeView, setActiveView] = useState<PlayerSquadRole>(initialView);

  useEffect(() => {
    setActiveView(initialView);
  }, [initialView]);

  const teamId = sessionState?.manager?.team_id ?? gameState?.manager?.team_id ?? null;
  const clockDate = sessionState?.clock.current_date ?? gameState?.clock.current_date ?? "";
  const [fetchedSquad, setFetchedSquad] = useFetchedSquad(teamId, clockDate);

  const team =
    sessionState?.team ??
    gameState?.teams.find((item) => item.id === teamId || item.manager_id === managerId) ??
    null;
  const players = fetchedSquad ?? gameState?.players.filter((player) => player.team_id === teamId) ?? [];

  const handleMutationComplete = (game: GameStateData) => {
    onGameUpdate?.(game);
    if (teamId) {
      setFetchedSquad(game.players.filter((player) => player.team_id === teamId));
    }
  };

  if (!team) {
    return <p className="text-gray-500 dark:text-gray-400">{t("common.unemployed")}</p>;
  }

  const counts = new Map<PlayerSquadRole, number>([
    ["Senior", 0],
    ["Reserve", 0],
    ["Youth", 0],
  ]);
  for (const player of players) {
    const role = getPlayerSquadRole(player);
    counts.set(role, (counts.get(role) ?? 0) + 1);
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-3 gap-1 rounded-xl border border-gray-200 bg-white p-1 dark:border-navy-600 dark:bg-navy-800">
        {views.map((view) => (
          <button
            key={view.id}
            type="button"
            onClick={() => setActiveView(view.id)}
            className={
              activeView === view.id
                ? "rounded-lg bg-primary-700 px-2 py-2 text-xs font-heading font-bold uppercase tracking-wide text-white shadow-sm"
                : "rounded-lg px-2 py-2 text-xs font-heading font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400"
            }
          >
            {view.label}
            <span className="ml-1 text-[10px] opacity-70">{counts.get(view.id) ?? 0}</span>
          </button>
        ))}
      </div>

      <SquadRosterView
        players={players}
        team={team}
        clockDate={clockDate}
        squadView={activeView}
        onSelectPlayer={onSelectPlayer}
        onMutationComplete={handleMutationComplete}
        sortState={sortState}
        onSortStateChange={onSortStateChange}
      />
    </div>
  );
}
