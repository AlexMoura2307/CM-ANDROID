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
