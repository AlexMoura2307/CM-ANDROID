import type { PlayerData } from "../store/gameStore";
import type { PlayerSquadRole } from "../store/types";
import { calcAge } from "./helpers";

export function getPlayerSquadRole(player: Pick<PlayerData, "squad_role">): PlayerSquadRole {
  if (player.squad_role === "Youth") return "Youth";
  if (player.squad_role === "Reserve") return "Reserve";
  return "Senior";
}

export function isYouthAcademyPlayer(player: Pick<PlayerData, "squad_role">): boolean {
  return getPlayerSquadRole(player) === "Youth";
}

export function isReserveSquadPlayer(player: Pick<PlayerData, "squad_role">): boolean {
  return getPlayerSquadRole(player) === "Reserve";
}

export function isSeniorSquadPlayer(player: Pick<PlayerData, "squad_role">): boolean {
  return getPlayerSquadRole(player) === "Senior";
}

export function canDelegateToYouthAcademy(
  player: Pick<PlayerData, "date_of_birth" | "squad_role">,
): boolean {
  return getPlayerSquadRole(player) !== "Youth" && calcAge(player.date_of_birth) <= 21;
}
