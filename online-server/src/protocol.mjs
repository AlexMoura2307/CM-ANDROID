export const ONLINE_PROTOCOL_VERSION = 1;

export const ClientMessage = Object.freeze({
  HELLO: "hello",
  CREATE_ROOM: "create_room",
  JOIN_ROOM: "join_room",
  RESUME_SESSION: "resume_session",
  SYNC_REQUEST: "sync_request",
  LEAVE_ROOM: "leave_room",
  READY: "ready",
  START_GAME: "start_game",
  COMMAND: "command",
  ADVANCE_DAY_READY: "advance_day_ready",
  PING: "ping",
});

export const ServerMessage = Object.freeze({
  WELCOME: "welcome",
  ROOM_CREATED: "room_created",
  SESSION_RESUMED: "session_resumed",
  ROOM_STATE: "room_state",
  GAME_STARTED: "game_started",
  SYNC_STATE: "sync_state",
  COMMAND_ACCEPTED: "command_accepted",
  DAY_ADVANCED: "day_advanced",
  ERROR: "error",
  PONG: "pong",
});

export function isNonEmptyString(value, max = 128) {
  return typeof value === "string" && value.trim().length > 0 && value.length <= max;
}

export function assertEnvelope(message) {
  if (!message || typeof message !== "object" || Array.isArray(message)) {
    throw new Error("invalid_message");
  }
  if (!isNonEmptyString(message.type, 64)) {
    throw new Error("invalid_message_type");
  }
  if (message.protocolVersion !== ONLINE_PROTOCOL_VERSION) {
    throw new Error("protocol_version_mismatch");
  }
  return message;
}

export function sanitizeManagerName(value) {
  if (!isNonEmptyString(value, 60)) throw new Error("invalid_manager_name");
  return value.trim();
}

export function sanitizeTeamId(value) {
  if (!isNonEmptyString(value, 128)) throw new Error("invalid_team_id");
  return value.trim();
}
