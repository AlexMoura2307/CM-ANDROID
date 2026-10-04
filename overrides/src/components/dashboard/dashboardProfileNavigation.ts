import type { PlayerSelectionOptions } from "../../store/gameStore";

export interface DashboardNavigateContext {
  messageId?: string;
}

export interface DashboardProfileHistoryEntry {
  tab: string;
  playerId: string | null;
  playerOptions: PlayerSelectionOptions | null;
  teamId: string | null;
  initialMessageId: string | null;
}

export interface DashboardProfileNavigationState {
  activeTab: string;
  selectedPlayerId: string | null;
  selectedPlayerOptions: PlayerSelectionOptions | null;
  selectedTeamId: string | null;
  initialMessageId: string | null;
  navHistory: DashboardProfileHistoryEntry[];
}

export function createDashboardProfileNavigationState(
  activeTab: string,
): DashboardProfileNavigationState {
  return {
    activeTab,
    selectedPlayerId: null,
    selectedPlayerOptions: null,
    selectedTeamId: null,
    initialMessageId: null,
    navHistory: [],
  };
}

export function clearDashboardProfileSelection(
  state: DashboardProfileNavigationState,
): DashboardProfileNavigationState {
  return {
    ...state,
    selectedPlayerId: null,
    selectedPlayerOptions: null,
    selectedTeamId: null,
  };
}

function currentEntry(state: DashboardProfileNavigationState): DashboardProfileHistoryEntry {
  return {
    tab: state.activeTab,
    playerId: state.selectedPlayerId,
    playerOptions: state.selectedPlayerOptions,
    teamId: state.selectedTeamId,
    initialMessageId: state.initialMessageId,
  };
}

export function resetDashboardToTab(
  state: DashboardProfileNavigationState,
  tab: string,
  messageId?: string,
): DashboardProfileNavigationState {
  return {
    ...clearDashboardProfileSelection(state),
    activeTab: tab,
    initialMessageId: messageId ?? null,
    navHistory: state.navHistory,
  };
}

export function pushDashboardHistory(
  state: DashboardProfileNavigationState,
): DashboardProfileNavigationState {
  const history = [...state.navHistory, currentEntry(state)].slice(-60);
  return {
    ...state,
    navHistory: history,
  };
}

export function navigateDashboardProfiles(
  state: DashboardProfileNavigationState,
  tab: string,
  context?: DashboardNavigateContext,
): DashboardProfileNavigationState {
  if (tab === "__selectTeam" && context?.messageId) {
    return {
      ...pushDashboardHistory(state),
      selectedTeamId: context.messageId,
      selectedPlayerId: null,
      selectedPlayerOptions: null,
    };
  }

  if (tab === "__selectPlayer" && context?.messageId) {
    return {
      ...pushDashboardHistory(state),
      selectedPlayerId: context.messageId,
      selectedPlayerOptions: null,
      selectedTeamId: null,
    };
  }

  if (
    tab === state.activeTab &&
    state.selectedPlayerId === null &&
    state.selectedTeamId === null &&
    (context?.messageId ?? null) === state.initialMessageId
  ) {
    return state;
  }

  const withHistory = pushDashboardHistory(state);
  return {
    ...clearDashboardProfileSelection(withHistory),
    activeTab: tab,
    initialMessageId: context?.messageId ?? null,
  };
}

export function goBackDashboardProfile(
  state: DashboardProfileNavigationState,
): DashboardProfileNavigationState {
  if (state.navHistory.length === 0) {
    if (state.selectedPlayerId !== null || state.selectedTeamId !== null) {
      return clearDashboardProfileSelection(state);
    }
    if (state.activeTab !== "Home") {
      return {
        ...clearDashboardProfileSelection(state),
        activeTab: "Home",
        initialMessageId: null,
      };
    }
    return state;
  }

  const previous = state.navHistory[state.navHistory.length - 1];

  return {
    ...state,
    activeTab: previous.tab,
    selectedPlayerId: previous.playerId,
    selectedPlayerOptions: previous.playerOptions,
    selectedTeamId: previous.teamId,
    initialMessageId: previous.initialMessageId,
    navHistory: state.navHistory.slice(0, -1),
  };
}

export function selectDashboardPlayer(
  state: DashboardProfileNavigationState,
  id: string,
  options?: PlayerSelectionOptions,
): DashboardProfileNavigationState {
  return {
    ...pushDashboardHistory(state),
    selectedPlayerId: id,
    selectedPlayerOptions: options ?? null,
    selectedTeamId: null,
  };
}

export function selectDashboardTeam(
  state: DashboardProfileNavigationState,
  id: string,
): DashboardProfileNavigationState {
  return {
    ...pushDashboardHistory(state),
    selectedTeamId: id,
    selectedPlayerId: null,
    selectedPlayerOptions: null,
  };
}

export function openDashboardSearchPlayer(
  state: DashboardProfileNavigationState,
  id: string,
): DashboardProfileNavigationState {
  return selectDashboardPlayer(state, id);
}

export function openDashboardSearchTeam(
  state: DashboardProfileNavigationState,
  id: string,
): DashboardProfileNavigationState {
  return selectDashboardTeam(state, id);
}

export function hasDashboardProfileHistory(state: DashboardProfileNavigationState): boolean {
  return (
    state.navHistory.length > 0 ||
    state.selectedPlayerId !== null ||
    state.selectedTeamId !== null ||
    state.activeTab !== "Home"
  );
}
