import test from "node:test";
import assert from "node:assert/strict";
import { RoomStore } from "../src/roomStore.mjs";

test("one human cannot take a club already controlled by another human", () => {
  const store = new RoomStore();
  const { room } = store.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
  });

  assert.throws(
    () =>
      store.joinRoom({
        code: room.code,
        connectionId: "b",
        managerName: "Manager B",
        teamId: "sao-paulo",
      }),
    /team_already_controlled/,
  );
});

test("a client cannot submit commands scoped to another human club", () => {
  const store = new RoomStore();
  const { room } = store.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
  });
  store.joinRoom({
    code: room.code,
    connectionId: "b",
    managerName: "Manager B",
    teamId: "flamengo",
  });

  assert.throws(
    () =>
      store.submitCommand("a", {
        clientCommandId: "cmd-1",
        kind: "set_lineup",
        teamId: "flamengo",
        payload: {},
      }),
    /forbidden_team_scope/,
  );
});

test("day only advances when every connected human is ready and opted to continue", () => {
  const store = new RoomStore();
  const { room } = store.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
  });
  store.joinRoom({
    code: room.code,
    connectionId: "b",
    managerName: "Manager B",
    teamId: "flamengo",
  });

  store.setReady("a", true);
  store.setReady("b", true);

  const first = store.markAdvanceReady("a", true);
  assert.equal(first.advanced, false);
  assert.equal(room.dayRevision, 0);

  const second = store.markAdvanceReady("b", true);
  assert.equal(second.advanced, true);
  assert.equal(room.dayRevision, 1);
});


test("disconnected human can resume the same manager and club without losing identity", () => {
  const store = new RoomStore();
  const { room, member } = store.createRoom({
    connectionId: "old-connection",
    managerName: "Manager A",
    teamId: "sao-paulo",
  });
  const token = member.resumeToken;
  const memberId = member.id;

  store.disconnect("old-connection");
  const resumed = store.resumeSession({
    connectionId: "new-connection",
    resumeToken: token,
  });

  assert.equal(resumed.room.code, room.code);
  assert.equal(resumed.member.id, memberId);
  assert.equal(resumed.member.teamId, "sao-paulo");
  assert.equal(resumed.member.connected, true);
  assert.equal(store.findMembership("old-connection"), null);
  assert.equal(store.findMembership("new-connection")?.member.id, memberId);
});

test("resume token is private and never appears in public room state", () => {
  const store = new RoomStore();
  const { room, member } = store.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
  });

  const publicState = store.publicState(room);
  assert.equal(publicState.members[0].id, member.id);
  assert.equal("resumeToken" in publicState.members[0], false);
});

test("client command retries are idempotent", () => {
  const store = new RoomStore();
  store.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
  });

  const command = {
    clientCommandId: "same-command-123",
    kind: "set_lineup",
    teamId: "sao-paulo",
    payload: { playerIds: ["p1", "p2"] },
  };
  const first = store.submitCommand("a", command);
  const second = store.submitCommand("a", command);

  assert.equal(first.duplicate, false);
  assert.equal(second.duplicate, true);
  assert.equal(second.entry.id, first.entry.id);
  assert.equal(first.room.commands.length, 1);
});

test("sync returns only commands newer than the client's revision", () => {
  const store = new RoomStore();
  store.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
  });

  const first = store.submitCommand("a", {
    clientCommandId: "cmd-1",
    kind: "set_lineup",
    teamId: "sao-paulo",
    payload: { playerIds: ["p1", "p2"] },
  });
  store.submitCommand("a", {
    clientCommandId: "cmd-2",
    kind: "set_tactics",
    teamId: "sao-paulo",
    payload: {},
  });

  const sync = store.syncSince("a", first.entry.revision);
  assert.equal(sync.commands.length, 1);
  assert.equal(sync.commands[0].clientCommandId, "cmd-2");
});


test("server is the source of truth for career date and advances exactly one day", () => {
  const store = new RoomStore();
  const { room } = store.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
    startDate: "2026-03-14",
  });
  store.joinRoom({
    code: room.code,
    connectionId: "b",
    managerName: "Manager B",
    teamId: "flamengo",
  });

  assert.equal(room.currentDate, "2026-03-14");
  store.setReady("a", true);
  store.setReady("b", true);
  store.markAdvanceReady("a", true);
  const result = store.markAdvanceReady("b", true);

  assert.equal(result.advanced, true);
  assert.equal(room.currentDate, "2026-03-15");
  assert.equal(room.dayRevision, 1);
});

test("invalid online career start date is rejected", () => {
  const store = new RoomStore();
  assert.throws(
    () =>
      store.createRoom({
        connectionId: "a",
        managerName: "Manager A",
        teamId: "sao-paulo",
        startDate: "2026-02-31",
      }),
    /invalid_start_date/,
  );
});


test("online room rejects a client using a different world database", () => {
  const store = new RoomStore();
  const { room } = store.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
    worldFingerprint: "south-america-2026:abc123",
  });

  assert.throws(
    () =>
      store.joinRoom({
        code: room.code,
        connectionId: "b",
        managerName: "Manager B",
        teamId: "flamengo",
        worldFingerprint: "south-america-2026:def456",
      }),
    /world_version_mismatch/,
  );
});

test("online room exposes the database fingerprint used by every human", () => {
  const store = new RoomStore();
  const { room } = store.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
    worldFingerprint: "south-america-2026:abc123",
  });

  assert.equal(
    store.publicState(room).worldFingerprint,
    "south-america-2026:abc123",
  );
});


test("multiplayer room snapshot survives server restart and can be resumed", () => {
  const firstStore = new RoomStore();
  const { room, member } = firstStore.createRoom({
    connectionId: "before-restart",
    managerName: "Manager A",
    teamId: "sao-paulo",
    startDate: "2026-04-01",
    worldFingerprint: "south-america-2026:abc123",
  });

  firstStore.setReady("before-restart", true);
  firstStore.submitCommand("before-restart", {
    clientCommandId: "persisted-command",
    kind: "set_tactics",
    teamId: "sao-paulo",
    payload: { mentality: "balanced" },
  });

  const snapshot = firstStore.serializeSnapshot();
  const secondStore = new RoomStore(snapshot);
  const restoredRoom = secondStore.getRoom(room.code);

  assert.ok(restoredRoom);
  assert.equal(restoredRoom.currentDate, "2026-04-01");
  assert.equal(restoredRoom.worldFingerprint, "south-america-2026:abc123");
  assert.equal(restoredRoom.commands.length, 1);

  const restoredMember = [...restoredRoom.members.values()][0];
  assert.equal(restoredMember.connected, false);
  assert.equal(restoredMember.ready, false);

  const resumed = secondStore.resumeSession({
    connectionId: "after-restart",
    resumeToken: member.resumeToken,
  });
  assert.equal(resumed.member.id, member.id);
  assert.equal(resumed.member.teamId, "sao-paulo");

  const sync = secondStore.syncSince("after-restart", 0);
  assert.equal(sync.commands.length, 1);
  assert.equal(sync.commands[0].clientCommandId, "persisted-command");
});

test("invalid multiplayer snapshot is rejected", () => {
  assert.throws(
    () => new RoomStore({ version: 999, rooms: [] }),
    /invalid_room_snapshot/,
  );
});


test("only the host can start and every connected human must be ready", () => {
  const store = new RoomStore();
  const { room } = store.createRoom({
    connectionId: "host",
    managerName: "Host",
    teamId: "sao-paulo",
  });
  store.joinRoom({
    code: room.code,
    connectionId: "guest",
    managerName: "Guest",
    teamId: "flamengo",
  });

  assert.throws(() => store.startGame("guest"), /only_room_owner_can_start/);
  store.setReady("host", true);
  assert.throws(() => store.startGame("host"), /not_all_managers_ready/);

  store.setReady("guest", true);
  const started = store.startGame("host");
  assert.equal(started.room.phase, "active");
  assert.ok(started.room.startedAt);
});

test("new managers cannot join after multiplayer game starts", () => {
  const store = new RoomStore();
  const { room } = store.createRoom({
    connectionId: "host",
    managerName: "Host",
    teamId: "sao-paulo",
  });
  store.joinRoom({
    code: room.code,
    connectionId: "guest",
    managerName: "Guest",
    teamId: "flamengo",
  });
  store.setReady("host", true);
  store.setReady("guest", true);
  store.startGame("host");

  assert.throws(
    () =>
      store.joinRoom({
        code: room.code,
        connectionId: "late",
        managerName: "Late",
        teamId: "palmeiras",
      }),
    /room_already_started/,
  );
});


test("server rejects command kinds that are not part of the CM online protocol", () => {
  const store = new RoomStore();
  store.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
  });

  assert.throws(
    () =>
      store.submitCommand("a", {
        clientCommandId: "cmd-unknown",
        kind: "edit_other_club",
        teamId: "sao-paulo",
        payload: {},
      }),
    /unsupported_command_kind/,
  );
});

test("market actions may target another club but must originate from the human club", () => {
  const store = new RoomStore();
  store.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
  });

  const result = store.submitCommand("a", {
    clientCommandId: "cmd-scout",
    kind: "scout_player",
    teamId: "sao-paulo",
    payload: {
      playerId: "player-123",
      targetClubId: "flamengo",
    },
  });

  assert.equal(result.entry.managerTeamId, "sao-paulo");
  assert.equal(result.entry.kind, "scout_player");
});

test("online command payload has a hard server-side size limit", () => {
  const store = new RoomStore();
  store.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
  });

  assert.throws(
    () =>
      store.submitCommand("a", {
        clientCommandId: "cmd-large",
        kind: "set_tactics",
        teamId: "sao-paulo",
        payload: { blob: "x".repeat(70 * 1024) },
      }),
    /command_payload_too_large/,
  );
});


test("each human receives only their own authoritative club state", () => {
  const store = new RoomStore();
  const { room, member: host } = store.createRoom({
    connectionId: "host",
    managerName: "Host",
    teamId: "sao-paulo",
  });
  const { member: guest } = store.joinRoom({
    code: room.code,
    connectionId: "guest",
    managerName: "Guest",
    teamId: "flamengo",
  });

  store.submitCommand("host", {
    clientCommandId: "sp-tactics",
    kind: "set_tactics",
    teamId: "sao-paulo",
    payload: { mentality: "attacking", press: "high" },
  });
  store.submitCommand("guest", {
    clientCommandId: "fla-tactics",
    kind: "set_tactics",
    teamId: "flamengo",
    payload: { mentality: "balanced", press: "medium" },
  });

  const hostState = store.privateState(room, host.id);
  const guestState = store.privateState(room, guest.id);

  assert.deepEqual(hostState.myClubState.tactics, {
    mentality: "attacking",
    press: "high",
  });
  assert.deepEqual(guestState.myClubState.tactics, {
    mentality: "balanced",
    press: "medium",
  });
  assert.equal("clubStates" in hostState, false);
  assert.equal("clubStates" in guestState, false);
});

test("incremental sync never leaks another human manager's private commands", () => {
  const store = new RoomStore();
  const { room } = store.createRoom({
    connectionId: "host",
    managerName: "Host",
    teamId: "sao-paulo",
  });
  store.joinRoom({
    code: room.code,
    connectionId: "guest",
    managerName: "Guest",
    teamId: "flamengo",
  });

  store.submitCommand("host", {
    clientCommandId: "sp-lineup",
    kind: "set_lineup",
    teamId: "sao-paulo",
    payload: { playerIds: ["sp1", "sp2"] },
  });
  store.submitCommand("guest", {
    clientCommandId: "fla-lineup",
    kind: "set_lineup",
    teamId: "flamengo",
    payload: { playerIds: ["fla1", "fla2"] },
  });

  const hostSync = store.syncSince("host", 0);
  const guestSync = store.syncSince("guest", 0);

  assert.deepEqual(hostSync.commands.map((x) => x.clientCommandId), ["sp-lineup"]);
  assert.deepEqual(guestSync.commands.map((x) => x.clientCommandId), ["fla-lineup"]);
});

test("authoritative lineup validates uniqueness and persists in club state", () => {
  const store = new RoomStore();
  const { room, member } = store.createRoom({
    connectionId: "host",
    managerName: "Host",
    teamId: "sao-paulo",
  });

  assert.throws(
    () =>
      store.submitCommand("host", {
        clientCommandId: "duplicate-lineup",
        kind: "set_lineup",
        teamId: "sao-paulo",
        payload: { playerIds: ["p1", "p1"] },
      }),
    /invalid_lineup_payload/,
  );

  store.submitCommand("host", {
    clientCommandId: "valid-lineup",
    kind: "set_lineup",
    teamId: "sao-paulo",
    payload: { playerIds: ["p1", "p2", "p3"] },
  });

  assert.deepEqual(
    store.privateState(room, member.id).myClubState.lineup,
    ["p1", "p2", "p3"],
  );
});

test("private club state survives multiplayer server snapshot restore", () => {
  const first = new RoomStore();
  const { room, member } = first.createRoom({
    connectionId: "a",
    managerName: "Manager A",
    teamId: "sao-paulo",
  });
  first.submitCommand("a", {
    clientCommandId: "lineup-before-restart",
    kind: "set_lineup",
    teamId: "sao-paulo",
    payload: { playerIds: ["p1", "p2"] },
  });

  const second = new RoomStore(first.serializeSnapshot());
  const restored = second.getRoom(room.code);
  const restoredState = second.privateState(restored, member.id);
  assert.deepEqual(restoredState.myClubState.lineup, ["p1", "p2"]);
});


test("a disconnected human blocks multiplayer game start", () => {
  const store = new RoomStore();
  const { room } = store.createRoom({
    connectionId: "host",
    managerName: "Host",
    teamId: "sao-paulo",
  });
  store.joinRoom({
    code: room.code,
    connectionId: "guest",
    managerName: "Guest",
    teamId: "flamengo",
  });

  store.setReady("host", true);
  store.setReady("guest", true);
  store.disconnect("guest");

  assert.throws(
    () => store.startGame("host"),
    /all_managers_must_be_connected/,
  );
});

test("a disconnected human blocks day advancement until reconnecting", () => {
  const store = new RoomStore();
  const { room, member: host } = store.createRoom({
    connectionId: "host",
    managerName: "Host",
    teamId: "sao-paulo",
  });
  const { member: guest } = store.joinRoom({
    code: room.code,
    connectionId: "guest",
    managerName: "Guest",
    teamId: "flamengo",
  });

  store.setReady("host", true);
  store.setReady("guest", true);
  store.markAdvanceReady("host", true);
  store.disconnect("guest");

  const blocked = store.markAdvanceReady("host", true);
  assert.equal(blocked.advanced, false);
  assert.equal(room.dayRevision, 0);

  store.resumeSession({
    connectionId: "guest-reconnected",
    resumeToken: guest.resumeToken,
  });
  store.setReady("guest-reconnected", true);
  const advanced = store.markAdvanceReady("guest-reconnected", true);

  assert.equal(advanced.advanced, true);
  assert.equal(room.dayRevision, 1);
  assert.equal(host.teamId, "sao-paulo");
});


test("human transfer offer is private to source and target clubs", () => {
  const store = new RoomStore();
  const { room, member: sp } = store.createRoom({
    connectionId: "sp",
    managerName: "SP Manager",
    teamId: "sao-paulo",
  });
  const { member: fla } = store.joinRoom({
    code: room.code,
    connectionId: "fla",
    managerName: "Fla Manager",
    teamId: "flamengo",
  });
  const { member: pal } = store.joinRoom({
    code: room.code,
    connectionId: "pal",
    managerName: "Pal Manager",
    teamId: "palmeiras",
  });

  store.submitCommand("sp", {
    clientCommandId: "offer-1",
    kind: "transfer_offer",
    teamId: "sao-paulo",
    payload: {
      playerId: "player-fla-9",
      targetClubId: "flamengo",
      amount: 12000000,
    },
  });

  const spState = store.privateState(room, sp.id);
  const flaState = store.privateState(room, fla.id);
  const palState = store.privateState(room, pal.id);

  assert.equal(spState.outgoingOffers.length, 1);
  assert.equal(spState.incomingOffers.length, 0);
  assert.equal(flaState.incomingOffers.length, 1);
  assert.equal(flaState.outgoingOffers.length, 0);
  assert.equal(palState.incomingOffers.length, 0);
  assert.equal(palState.outgoingOffers.length, 0);
  assert.equal("pendingOffers" in store.publicState(room), false);
});

test("only the club that owns the target side can answer a human transfer offer", () => {
  const store = new RoomStore();
  const { room } = store.createRoom({
    connectionId: "sp",
    managerName: "SP Manager",
    teamId: "sao-paulo",
  });
  store.joinRoom({
    code: room.code,
    connectionId: "fla",
    managerName: "Fla Manager",
    teamId: "flamengo",
  });

  store.submitCommand("sp", {
    clientCommandId: "offer-2",
    kind: "transfer_offer",
    teamId: "sao-paulo",
    payload: {
      playerId: "player-fla-10",
      targetClubId: "flamengo",
      amount: 8000000,
    },
  });
  const offerId = store.findMembership("sp").room.pendingOffers[0].id;

  assert.throws(
    () =>
      store.submitCommand("sp", {
        clientCommandId: "illegal-answer",
        kind: "respond_transfer_offer",
        teamId: "sao-paulo",
        payload: { offerId, decision: "accept" },
      }),
    /only_owner_club_can_answer_offer/,
  );

  store.submitCommand("fla", {
    clientCommandId: "valid-answer",
    kind: "respond_transfer_offer",
    teamId: "flamengo",
    payload: { offerId, decision: "reject" },
  });

  assert.equal(room.pendingOffers[0].status, "rejected");
  assert.ok(room.pendingOffers[0].respondedAt);
});

test("loan offer cannot be answered through transfer response command", () => {
  const store = new RoomStore();
  const { room } = store.createRoom({
    connectionId: "sp",
    managerName: "SP Manager",
    teamId: "sao-paulo",
  });
  store.joinRoom({
    code: room.code,
    connectionId: "fla",
    managerName: "Fla Manager",
    teamId: "flamengo",
  });

  store.submitCommand("sp", {
    clientCommandId: "loan-1",
    kind: "loan_offer",
    teamId: "sao-paulo",
    payload: {
      playerId: "player-fla-22",
      targetClubId: "flamengo",
      amount: 0,
    },
  });
  const offerId = room.pendingOffers[0].id;

  assert.throws(
    () =>
      store.submitCommand("fla", {
        clientCommandId: "wrong-response-kind",
        kind: "respond_transfer_offer",
        teamId: "flamengo",
        payload: { offerId, decision: "accept" },
      }),
    /market_offer_type_mismatch/,
  );

  store.submitCommand("fla", {
    clientCommandId: "loan-response",
    kind: "respond_loan_offer",
    teamId: "flamengo",
    payload: { offerId, decision: "accept" },
  });
  assert.equal(room.pendingOffers[0].status, "accepted");
});

test("pending negotiations survive multiplayer server restart", () => {
  const first = new RoomStore();
  const { room, member: sp } = first.createRoom({
    connectionId: "sp",
    managerName: "SP Manager",
    teamId: "sao-paulo",
  });
  first.joinRoom({
    code: room.code,
    connectionId: "fla",
    managerName: "Fla Manager",
    teamId: "flamengo",
  });
  first.submitCommand("sp", {
    clientCommandId: "persist-offer",
    kind: "transfer_offer",
    teamId: "sao-paulo",
    payload: {
      playerId: "player-fla-7",
      targetClubId: "flamengo",
      amount: 5000000,
    },
  });

  const second = new RoomStore(first.serializeSnapshot());
  const restored = second.getRoom(room.code);
  const sourceState = second.privateState(restored, sp.id);
  assert.equal(sourceState.outgoingOffers.length, 1);
  assert.equal(sourceState.outgoingOffers[0].amount, 5000000);
  assert.equal(sourceState.outgoingOffers[0].status, "pending");
});


test("scouting knowledge is isolated per human-controlled club", () => {
  const store = new RoomStore();
  const { room, member: sp } = store.createRoom({
    connectionId: "sp",
    managerName: "SP Manager",
    teamId: "sao-paulo",
  });
  const { member: fla } = store.joinRoom({
    code: room.code,
    connectionId: "fla",
    managerName: "Fla Manager",
    teamId: "flamengo",
  });

  store.submitCommand("sp", {
    clientCommandId: "scout-1",
    kind: "scout_player",
    teamId: "sao-paulo",
    payload: { playerId: "target-9", targetClubId: "palmeiras" },
  });

  const spState = store.privateState(room, sp.id);
  const flaState = store.privateState(room, fla.id);

  assert.equal(spState.myClubState.scoutingReports["target-9"].knowledge, 15);
  assert.equal(flaState.myClubState.scoutingReports["target-9"], undefined);
});

test("scouting knowledge advances with the shared career day without leaking", () => {
  const store = new RoomStore();
  const { room, member: sp } = store.createRoom({
    connectionId: "sp",
    managerName: "SP Manager",
    teamId: "sao-paulo",
  });
  const { member: fla } = store.joinRoom({
    code: room.code,
    connectionId: "fla",
    managerName: "Fla Manager",
    teamId: "flamengo",
  });

  store.submitCommand("sp", {
    clientCommandId: "scout-day-1",
    kind: "scout_player",
    teamId: "sao-paulo",
    payload: { playerId: "target-10", targetClubId: "corinthians" },
  });

  store.setReady("sp", true);
  store.setReady("fla", true);
  store.markAdvanceReady("sp", true);
  store.markAdvanceReady("fla", true);

  const spReport = store.privateState(room, sp.id).myClubState.scoutingReports["target-10"];
  const flaReport = store.privateState(room, fla.id).myClubState.scoutingReports["target-10"];

  assert.equal(spReport.knowledge, 27);
  assert.equal(spReport.lastUpdatedDayRevision, 1);
  assert.equal(flaReport, undefined);
});
