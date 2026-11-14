import { test } from "node:test";
import assert from "node:assert/strict";
import {
  APPLICATION_STATUSES,
  STATUS_TRANSITIONS,
  canConfirmSubmission,
  canTransition,
  isTerminal,
} from "../frontend/js/lib/status.js";

test("nothing can move to 'applied' through a normal status change", () => {
  for (const from of APPLICATION_STATUSES)
    assert.equal(canTransition(from, "applied"), false);
});

test("forward moves are allowed", () => {
  assert.ok(canTransition("saved", "preparing"));
  assert.ok(canTransition("preparing", "ready_for_review"));
  assert.ok(canTransition("applied", "interview"));
  assert.ok(canTransition("interview", "offer"));
});

test("backwards and skipped moves are refused", () => {
  assert.equal(canTransition("offer", "saved"), false);
  assert.equal(canTransition("rejected", "interview"), false);
  assert.equal(canTransition("saved", "offer"), false);
});

test("rejected and withdrawn are closed", () => {
  assert.ok(isTerminal("rejected"));
  assert.ok(isTerminal("withdrawn"));
  assert.equal(isTerminal("applied"), false);
});

test("you can only record as applied before applying", () => {
  assert.ok(canConfirmSubmission("ready_for_review"));
  assert.equal(canConfirmSubmission("applied"), false);
});

test("every status has a row in the transition table", () => {
  assert.deepEqual(
    Object.keys(STATUS_TRANSITIONS).sort(),
    [...APPLICATION_STATUSES].sort(),
  );
});
