import crypto from "node:crypto";
import { sanitizeManagerName, sanitizeTeamId } from "./protocol.mjs";

const CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

function makeCode(length = 6) {
  const bytes = crypto.randomBytes(length);
  let code = "";
  for (let i = 0; i < length; i += 1) {
    code += CODE_ALPHABET[bytes[i] % CODE_ALPHABET.length];
  }
  return code;
}

function normalizeWorldFingerprint(value) {
  const text = String(value || "").trim();
  if (!text || text.length > 160) throw new Error("invalid_world_fingerprint");
  if (!/^[A-Za-z0-9._:-]+$/.test(text)) throw new Error("invalid_world_fingerprint");
  return text;
}

function normalizeIsoDate(value) {
  const text = String(value || "").trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) throw new Error("invalid_start_date");
  const date = new Date(`${text}T00:00:00.000Z`);
  if (Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== text) {
    throw new Error("invalid_start_date");
  }
  return text;
}

function plusOneDay(isoDate) {
  const date = new Date(`${isoDate}T00:00:00.000Z`);
  date.setUTCDate(date.getUTCDate() + 1);
  return date.toISOString().slice(0, 10);
}

function publicMember(member) {
  return {
    id: member.id,
    managerName: member.managerName,
    teamId: member.teamId,
    ready: member.ready,
    connected: member.connected,
  };
}

export class RoomStore {
  constructor() {
    this.rooms = new Map();
  }

  createRoom({
    connectionId,
    managerName,
    teamId,
    startDate = "2026-01-01",
    worldFingerprint = "cm-dev-world",
  }) {
    let code = makeCode();
    while (this.rooms.has(code)) code = makeCode();

    const member = {
      id: crypto.randomUUID(),
      connectionId,
      resumeToken: crypto.randomBytes(24).toString("base64url"),
      managerName: sanitizeManagerName(managerName),
      teamId: sanitizeTeamId(teamId),
      ready: false,
      advanceReady: false,
      connected: true,
      joinedAt: Date.now(),
    };

    const room = {
      code,
      revision: 0,
      dayRevision: 0,
      currentDate: normalizeIsoDate(startDate),
      worldFingerprint: normalizeWorldFingerprint(worldFingerprint),
      ownerMemberId: member.id,
      members: new Map([[member.id, member]]),
      commands: [],
      createdAt: Date.now(),
    };
    this.rooms.set(code, room);
    return { room, member };
  }

  joinRoom({ code, connectionId, managerName, teamId, worldFingerprint = "cm-dev-world" }) {
    const room = this.rooms.get(String(code || "").trim().toUpperCase());
    if (!room) throw new Error("room_not_found");

    const expectedWorld = normalizeWorldFingerprint(worldFingerprint);
    if (room.worldFingerprint !== expectedWorld) {
      throw new Error("world_version_mismatch");
    }

    const normalizedTeamId = sanitizeTeamId(teamId);
    for (const member of room.members.values()) {
      if (member.teamId === normalizedTeamId) {
        throw new Error("team_already_controlled");
      }
    }

    const member = {
      id: crypto.randomUUID(),
      connectionId,
      resumeToken: crypto.randomBytes(24).toString("base64url"),
      managerName: sanitizeManagerName(managerName),
      teamId: normalizedTeamId,
      ready: false,
      advanceReady: false,
      connected: true,
      joinedAt: Date.now(),
    };
    room.members.set(member.id, member);
    room.revision += 1;
    return { room, member };
  }

  getRoom(code) {
    return this.rooms.get(String(code || "").trim().toUpperCase()) || null;
  }

  resumeSession({ connectionId, resumeToken }) {
    const token = String(resumeToken || "").trim();
    if (!token) throw new Error("invalid_resume_token");

    for (const room of this.rooms.values()) {
      for (const member of room.members.values()) {
        if (member.resumeToken !== token) continue;
        if (member.connected && member.connectionId !== connectionId) {
          throw new Error("session_already_connected");
        }
        member.connectionId = connectionId;
        member.connected = true;
        member.advanceReady = false;
        room.revision += 1;
        return { room, member };
      }
    }
    throw new Error("resume_session_not_found");
  }

  syncSince(connectionId, afterRevision = 0) {
    const found = this.findMembership(connectionId);
    if (!found) throw new Error("not_in_room");
    const revision = Number.isFinite(Number(afterRevision))
      ? Math.max(0, Math.floor(Number(afterRevision)))
      : 0;
    return {
      ...found,
      commands: found.room.commands.filter((entry) => entry.revision > revision),
    };
  }

  findMembership(connectionId) {
    for (const room of this.rooms.values()) {
      for (const member of room.members.values()) {
        if (member.connectionId === connectionId) return { room, member };
      }
    }
    return null;
  }

  setReady(connectionId, ready) {
    const found = this.findMembership(connectionId);
    if (!found) throw new Error("not_in_room");
    found.member.ready = Boolean(ready);
    found.room.revision += 1;
    return found;
  }

  submitCommand(connectionId, command) {
    const found = this.findMembership(connectionId);
    if (!found) throw new Error("not_in_room");
    if (!command || typeof command !== "object" || Array.isArray(command)) {
      throw new Error("invalid_command");
    }

    const clientCommandId = String(command.clientCommandId || "").trim().slice(0, 128);
    if (!clientCommandId) throw new Error("missing_client_command_id");

    const duplicate = found.room.commands.find(
      (entry) =>
        entry.memberId === found.member.id &&
        entry.clientCommandId === clientCommandId,
    );
    if (duplicate) {
      return { ...found, entry: duplicate, duplicate: true };
    }

    const scopeTeamId = String(command.teamId || "");
    if (scopeTeamId && scopeTeamId !== found.member.teamId) {
      throw new Error("forbidden_team_scope");
    }

    const entry = {
      id: crypto.randomUUID(),
      memberId: found.member.id,
      managerTeamId: found.member.teamId,
      clientCommandId,
      kind: String(command.kind || "").slice(0, 80),
      payload: command.payload ?? null,
      receivedAt: Date.now(),
      revision: found.room.revision + 1,
    };

    if (!entry.kind) throw new Error("invalid_command_kind");
    found.room.commands.push(entry);
    if (found.room.commands.length > 5000) found.room.commands.splice(0, 1000);
    found.room.revision = entry.revision;
    return { ...found, entry, duplicate: false };
  }

  markAdvanceReady(connectionId, ready) {
    const found = this.findMembership(connectionId);
    if (!found) throw new Error("not_in_room");
    found.member.advanceReady = Boolean(ready);
    found.room.revision += 1;

    const connectedMembers = [...found.room.members.values()].filter((m) => m.connected);
    const canAdvance =
      connectedMembers.length > 0 &&
      connectedMembers.every((m) => m.ready && m.advanceReady);

    if (canAdvance) {
      found.room.dayRevision += 1;
      found.room.currentDate = plusOneDay(found.room.currentDate);
      found.room.revision += 1;
      for (const member of found.room.members.values()) {
        member.advanceReady = false;
      }
    }

    return { ...found, advanced: canAdvance };
  }

  disconnect(connectionId) {
    const found = this.findMembership(connectionId);
    if (!found) return null;
    found.member.connected = false;
    found.member.ready = false;
    found.member.advanceReady = false;
    found.room.revision += 1;
    return found;
  }

  remove(connectionId) {
    const found = this.findMembership(connectionId);
    if (!found) return null;
    found.room.members.delete(found.member.id);
    found.room.revision += 1;
    if (found.room.members.size === 0) {
      this.rooms.delete(found.room.code);
      return { room: null, member: found.member, deleted: true };
    }
    if (found.room.ownerMemberId === found.member.id) {
      const next = [...found.room.members.values()].sort((a, b) => a.joinedAt - b.joinedAt)[0];
      found.room.ownerMemberId = next.id;
    }
    return { room: found.room, member: found.member, deleted: false };
  }

  publicState(room) {
    return {
      code: room.code,
      revision: room.revision,
      dayRevision: room.dayRevision,
      currentDate: room.currentDate,
      worldFingerprint: room.worldFingerprint,
      ownerMemberId: room.ownerMemberId,
      members: [...room.members.values()].map(publicMember),
    };
  }
}
