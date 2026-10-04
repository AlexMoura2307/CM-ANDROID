import { useEffect, useState } from "react";
import type { GameStateData } from "../../store/gameStore";
import {
  cancelYouthScouting,
  reassignYouthScouting,
  startYouthScouting,
} from "../../services/scoutingService";
import { calculateAvailableScouts } from "../scouting/ScoutingTab.helpers";
import ScoutingYouthRecruitmentCard from "../scouting/ScoutingYouthRecruitmentCard";

interface WFEYouthRecruitmentPanelProps {
  gameState: GameStateData;
  onGameUpdate?: (game: GameStateData) => void;
}

export default function WFEYouthRecruitmentPanel({
  gameState,
  onGameUpdate,
}: WFEYouthRecruitmentPanelProps) {
  const [startingYouthSearch, setStartingYouthSearch] = useState(false);
  const [selectedYouthScoutId, setSelectedYouthScoutId] = useState("");
  const [youthRegion, setYouthRegion] = useState("Domestic");
  const [youthObjective, setYouthObjective] = useState("Balanced");
  const [youthTargetPosition, setYouthTargetPosition] = useState("");
  const [youthSearchError, setYouthSearchError] = useState<string | null>(null);

  const teamId = gameState.manager.team_id ?? "";
  const scouts = gameState.staff.filter((staff) => staff.role === "Scout" && staff.team_id === teamId);
  const assignments = gameState.scouting_assignments ?? [];
  const youthAssignments = gameState.youth_scouting_assignments ?? [];
  const availableScouts = calculateAvailableScouts(scouts, [...assignments, ...youthAssignments]);

  useEffect(() => {
    if (selectedYouthScoutId && availableScouts.some((scout) => scout.id === selectedYouthScoutId)) {
      return;
    }
    setSelectedYouthScoutId(availableScouts[0]?.id ?? "");
  }, [availableScouts, selectedYouthScoutId]);

  const applyUpdate = (updated: GameStateData) => {
    onGameUpdate?.(updated);
  };

  const startSearch = async () => {
    if (!selectedYouthScoutId) return;
    setStartingYouthSearch(true);
    setYouthSearchError(null);
    try {
      const updated = await startYouthScouting({
        scoutId: selectedYouthScoutId,
        region: youthRegion,
        objective: youthObjective,
        targetPosition: youthTargetPosition || null,
      });
      applyUpdate(updated);
      setSelectedYouthScoutId("");
    } catch (error) {
      setYouthSearchError(String(error));
    } finally {
      setStartingYouthSearch(false);
    }
  };

  const cancelSearch = async (assignmentId: string) => {
    setYouthSearchError(null);
    try {
      applyUpdate(await cancelYouthScouting(assignmentId));
    } catch (error) {
      setYouthSearchError(String(error));
    }
  };

  const reassignSearch = async (assignmentId: string, scoutId: string) => {
    setYouthSearchError(null);
    try {
      applyUpdate(await reassignYouthScouting(assignmentId, scoutId));
    } catch (error) {
      setYouthSearchError(String(error));
    }
  };

  return (
    <div className="mb-4">
      <ScoutingYouthRecruitmentCard
        title="Recrutamento da Base"
        hint="Novos jogadores da Base entram pelo recrutamento. Envie um olheiro, aguarde o relatório e decida quem receberá proposta para a Base."
        youthAssignments={youthAssignments}
        scouts={scouts}
        availableScouts={availableScouts}
        isStarting={startingYouthSearch}
        selectedScoutId={selectedYouthScoutId}
        region={youthRegion}
        objective={youthObjective}
        targetPosition={youthTargetPosition}
        errorMessage={youthSearchError}
        onScoutChange={setSelectedYouthScoutId}
        onRegionChange={setYouthRegion}
        onObjectiveChange={setYouthObjective}
        onTargetPositionChange={setYouthTargetPosition}
        onStartSearch={() => void startSearch()}
        onCancelSearch={(assignmentId) => void cancelSearch(assignmentId)}
        onReassignSearch={(assignmentId, scoutId) => void reassignSearch(assignmentId, scoutId)}
      />
    </div>
  );
}
