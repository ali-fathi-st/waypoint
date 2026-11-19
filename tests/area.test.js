// The website's copy of the "is this remote job open to you?" rule. Same
// cases as backend/tests/test_sources_more.py, so the two can't drift apart.
import { test } from "node:test";
import assert from "node:assert/strict";
import { remoteOpenToYou, userArea } from "../frontend/js/lib/area.js";

const edmonton = userArea(["Edmonton, AB", "Calgary, AB"]);

test("remote jobs open to Canada count; other countries don't", () => {
  for (const [location, open] of [
    ["Remote - Canada", true],
    ["Remote, Canada; Remote, United States", true],
    ["Remote, United States", false],
    ["Remote - EMEA", false],
    ["Remote - SF Bay Area", false],
    ["Remote", true],
    [null, true],
    ["Anywhere (Remote)", true],
  ]) {
    assert.equal(remoteOpenToYou(location, edmonton), open, String(location));
  }
});

test("with no locations on the profile, everything is open", () => {
  assert.equal(remoteOpenToYou("Remote, United States", userArea([])), true);
});
