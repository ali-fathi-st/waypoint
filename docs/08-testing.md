# 8. Testing

Two kinds of checks: automated tests for the rules, and a short click-through
for the pages.

## Automated tests

```bash
npm test
```

Needs Node.js 22 or newer. There's nothing to install: the tests use Node's
built-in test runner. GitHub runs them before every deployment and publishes
only if they pass.

| File | Checks |
| --- | --- |
| `tests/format.test.js` | Date maths (calendar dates never shift by time zone), relative dates, salary formatting |
| `tests/status.test.js` | Which status changes are allowed; "applied" never directly |
| `tests/mock-api.test.js` | The application rules (one per job, confirmation step, closing clears follow-ups), filters, scoring, scenarios, and that sample data has every field the contract requires |
| `tests/http-api.test.js` | Backend calls with a fake server: URLs, error messages, missing-field detection, network failures |
| `tests/api.test.js` | Hybrid mode sends the right operations to the right place |

`mock-api.test.js` doubles as a checklist for the backend: every rule it
tests, FastAPI enforces too, and `backend/tests/test_applications.py` is its
pytest port. The backend's own tests run with `pytest` from the `backend`
folder; see [09 The backend](09-backend.md#8-tests).

### Writing a test

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { addDays } from "../frontend/js/lib/format.js";

test("adds a week", () => {
  assert.equal(addDays("2026-11-14", 7), "2026-11-21");
});
```

Save it as `tests/<something>.test.js`; `npm test` finds it.

## Click-through checklist

Do this after changing a page (5 minutes). Start the local server
([01](01-getting-started.md)) and reset the sample data first
(Settings → Developer → Reset sample data).

**Every page**

- [ ] Loads without errors in `F12` → Console
- [ ] Works at phone width (`F12` → device toolbar → a phone) with no sideways scrolling
- [ ] Tab through it: focus is always visible; dialogs close with Esc

**Main workflow**

- [ ] Jobs: type in Title; the list narrows and the address bar updates; refresh keeps the filter
- [ ] Shortlist a job (star): "Shortlisted" appears
- [ ] Open a job: the match points add up to the score
- [ ] Start application: you land on the application page
- [ ] Move to... Preparing: the badge and timeline update
- [ ] Record as applied without ticking the boxes: two errors appear
- [ ] Tick both and record: status Applied, follow-up 14 days later, timeline entry
- [ ] Add interview: status becomes Interview
- [ ] Save notes, refresh: the notes are still there
- [ ] Move to... Withdrawn: asks first, then the status menu disappears

**Other pages**

- [ ] Applications: switch Board / Table; "Follow-ups due" filters
- [ ] Documents: upload with no name shows errors; with a PDF it appears as a new version
- [ ] Profile: clear your name and save: error; add a skill and save: "Profile saved"
- [ ] Settings: change a source and save; account with a bad email shows an error

**States** (Settings → Developer)

- [ ] Empty: pages explain what to do instead of showing blank areas
- [ ] Slow: grey placeholders appear while loading
- [ ] Error: a red message with "Try again"
- [ ] Back to Normal

## What was tested before publishing

The first version was checked by an automated browser run of the whole
checklist above, at desktop and phone sizes, served under `/waypoint/` exactly
like GitHub Pages, with zero console errors and no sideways scrolling.
