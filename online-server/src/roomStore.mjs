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

  createRoom({ connectionId, managerName, teamId }) {
    let code = makeCode();
    while (this.rooms.has(code)) code = makeCode();

    const member = {
      id: crypto.randomUUID(),
      connectionId,
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
      ownerMemberId: member.id,
      members: new Map([[member.id, member]]),
      commands: [],
      createdAt: Date.now(),
    };
    this.rooms.set(code, room);
    return { room, member };
  }

  joinRoom({ code, connectionId, managerName, teamId }) {
    const room = this.rooms.get(String(code || "").trim().toUpperCase());
    if (!room) throw new Error("room_not_found");

    const normalizedTeamId = sanitizeTeamId(teamId);
    for (const member of room.members.values()) {
      if (member.teamId === normalizedTeamId) {
        throw new Error("team_already_controlled");
      }
    }

    const member = {
      id: crypto.randomUUID(),
      connectionId,
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

    const scopeTeamId = String(command.teamId || "");
    if (scopeTeamId && scopeTeamId !== found.member.teamId) {
      throw new Error("forbidden_team_scope");
    }

    const entry = {
      id: crypto.randomUUID(),
      memberId: found.member.id,
      managerTeamId: found.member.teamId,
      clientCommandId: String(command.clientCommandId || "").slice(0, 128),
      kind: String(command.kind || "").slice(0, 80),
      payload: command.payload ?? null,
      receivedAt: Date.now(),
      revision: found.room.revision + 1,
    };

    if (!entry.kind) throw new Error("invalid_command_kind");
    found.room.commands.push(entry);
    if (found.room.commands.length > 5000) found.room.commands.splice(0, 1000);
    found.room.revision = entry.revision;
    return { ...found, entry };
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
      ownerMemberId: room.ownerMemberId,
      members: [...room.members.values()].map(publicMember),
    };
  }
}
