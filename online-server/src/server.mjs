import http from "node:http";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { WebSocketServer, WebSocket } from "ws";
import {
  ONLINE_PROTOCOL_VERSION,
  ClientMessage,
  ServerMessage,
  assertEnvelope,
} from "./protocol.mjs";
import { RoomStore } from "./roomStore.mjs";

const PORT = Number(process.env.PORT || 8787);
const STATE_FILE = process.env.CM_ONLINE_STATE_FILE || "./data/cm-online-state.json";

function loadSnapshot() {
  try {
    if (!fs.existsSync(STATE_FILE)) return null;
    return JSON.parse(fs.readFileSync(STATE_FILE, "utf8"));
  } catch (e) {
    console.error("Failed to load online snapshot:", e);
    return null;
  }
}

const store = new RoomStore(loadSnapshot());
const sockets = new Map();

function persistSnapshot() {
  try {
    const dir = path.dirname(STATE_FILE);
    fs.mkdirSync(dir, { recursive: true });
    const tmp = `${STATE_FILE}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(store.serializeSnapshot()), "utf8");
    fs.renameSync(tmp, STATE_FILE);
  } catch (e) {
    console.error("Failed to persist online snapshot:", e);
  }
}

function send(ws, type, payload = {}) {
  if (ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({ protocolVersion: ONLINE_PROTOCOL_VERSION, type, ...payload }));
}

function error(ws, code, detail = null) {
  send(ws, ServerMessage.ERROR, { code, detail });
}

function broadcastRoom(room) {
  if (!room) return;
  for (const member of room.members.values()) {
    const ws = sockets.get(member.connectionId);
    if (ws) {
      send(ws, ServerMessage.ROOM_STATE, {
        room: store.privateState(room, member.id),
      });
    }
  }
}

const server = http.createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ ok: true, protocolVersion: ONLINE_PROTOCOL_VERSION }));
    return;
  }
  res.writeHead(404, { "content-type": "application/json" });
  res.end(JSON.stringify({ error: "not_found" }));
});

const wss = new WebSocketServer({ server, path: "/ws", maxPayload: 256 * 1024 });

wss.on("connection", (ws) => {
  const connectionId = crypto.randomUUID();
  sockets.set(connectionId, ws);
  send(ws, ServerMessage.WELCOME, { connectionId });

  ws.on("message", (raw) => {
    let msg;
    try {
      msg = assertEnvelope(JSON.parse(raw.toString("utf8")));
    } catch (e) {
      error(ws, e instanceof Error ? e.message : "invalid_message");
      return;
    }

    try {
      switch (msg.type) {
        case ClientMessage.HELLO:
          send(ws, ServerMessage.WELCOME, { connectionId });
          break;

        case ClientMessage.CREATE_ROOM: {
          if (store.findMembership(connectionId)) throw new Error("already_in_room");
          const { room, member } = store.createRoom({
            connectionId,
            managerName: msg.managerName,
            teamId: msg.teamId,
            startDate: msg.startDate,
            worldFingerprint: msg.worldFingerprint,
          });
          send(ws, ServerMessage.ROOM_CREATED, {
            room: store.privateState(room, member.id),
            memberId: member.id,
            resumeToken: member.resumeToken,
          });
          broadcastRoom(room);
          persistSnapshot();
          break;
        }

        case ClientMessage.JOIN_ROOM: {
          if (store.findMembership(connectionId)) throw new Error("already_in_room");
          const { room, member } = store.joinRoom({
            code: msg.code,
            connectionId,
            managerName: msg.managerName,
            teamId: msg.teamId,
            worldFingerprint: msg.worldFingerprint,
          });
          send(ws, ServerMessage.ROOM_STATE, {
            room: store.privateState(room, member.id),
            memberId: member.id,
            resumeToken: member.resumeToken,
          });
          broadcastRoom(room);
          persistSnapshot();
          break;
        }

        case ClientMessage.RESUME_SESSION: {
          if (store.findMembership(connectionId)) throw new Error("already_in_room");
          const { room, member } = store.resumeSession({
            connectionId,
            resumeToken: msg.resumeToken,
          });
          send(ws, ServerMessage.SESSION_RESUMED, {
            room: store.privateState(room, member.id),
            memberId: member.id,
            resumeToken: member.resumeToken,
          });
          broadcastRoom(room);
          persistSnapshot();
          break;
        }

        case ClientMessage.SYNC_REQUEST: {
          const { room, commands } = store.syncSince(connectionId, msg.afterRevision);
          send(ws, ServerMessage.SYNC_STATE, {
            room: store.privateState(room, member.id),
            commands,
          });
          break;
        }

        case ClientMessage.READY: {
          const { room } = store.setReady(connectionId, msg.ready);
          broadcastRoom(room);
          persistSnapshot();
          break;
        }

        case ClientMessage.START_GAME: {
          const { room } = store.startGame(connectionId);
          for (const member of room.members.values()) {
            const peer = sockets.get(member.connectionId);
            if (peer) {
              send(peer, ServerMessage.GAME_STARTED, {
                room: store.privateState(room, member.id),
              });
            }
          }
          broadcastRoom(room);
          persistSnapshot();
          break;
        }

        case ClientMessage.COMMAND: {
          const { room, entry, duplicate } = store.submitCommand(connectionId, msg.command);
          send(ws, ServerMessage.COMMAND_ACCEPTED, {
            commandId: entry.id,
            clientCommandId: entry.clientCommandId,
            revision: entry.revision,
            duplicate,
          });
          broadcastRoom(room);
          persistSnapshot();
          break;
        }

        case ClientMessage.ADVANCE_DAY_READY: {
          const result = store.markAdvanceReady(connectionId, msg.ready);
          if (result.advanced) {
            for (const member of result.room.members.values()) {
              const peer = sockets.get(member.connectionId);
              if (peer) {
                send(peer, ServerMessage.DAY_ADVANCED, {
                  dayRevision: result.room.dayRevision,
                  currentDate: result.room.currentDate,
                  revision: result.room.revision,
                });
              }
            }
          }
          broadcastRoom(result.room);
          persistSnapshot();
          break;
        }

        case ClientMessage.LEAVE_ROOM: {
          const result = store.remove(connectionId);
          if (result?.room) broadcastRoom(result.room);
          persistSnapshot();
          break;
        }

        case ClientMessage.PING:
          send(ws, ServerMessage.PONG, { now: Date.now() });
          break;

        default:
          throw new Error("unsupported_message_type");
      }
    } catch (e) {
      error(ws, e instanceof Error ? e.message : "server_error");
    }
  });

  ws.on("close", () => {
    sockets.delete(connectionId);
    const found = store.disconnect(connectionId);
    if (found?.room) broadcastRoom(found.room);
    persistSnapshot();
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`CM online server listening on :${PORT}`);
});
