# Tests

Plain JavaScript tests using Node's built-in test runner. Nothing to install.

```bash
npm test          # or: node --test "tests/*.test.js"
```

They cover the logic that has rules: dates, status changes, the mock API
(which mirrors what the backend must do), the HTTP API's error handling, and
the hybrid mode switch. Pages themselves are checked by clicking through them
in a browser (see docs/08-testing.md).
