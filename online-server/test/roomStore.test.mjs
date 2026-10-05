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
    payload: {},
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
