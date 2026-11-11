# Part 4 evidence

Verified on 10 November 2026.

- [Full local test output](test-results.txt): Ruff passed; **52 tests passed**.
- [JUnit results](test-results.xml): machine-readable results.
- [Deliberate bug: failing test](regression-failing.txt): expected exit 1, boolean quantity was wrongly accepted.
- [Corrected check: passing test](regression-fixed.txt): exit 0 for the same test.
- [Public checker](worker/public-checker.txt): **15 passed / 0 failed / 0 skipped**, with both flags.
- Worker recovery/poison logs from this run are in `worker/`; the separate Part 3 evidence is unchanged.

The full test output includes both distinct concurrency tests, real API process IDs and database snapshots. Same-key race: one order, stock six. Different-key race: seven accepted, five rejected, stock zero.

Repeat the bug demo with `python scripts/regression_demo.py`. It introduces and repairs the bug only in a temporary source copy. The working code and database are untouched. This is not CI red-to-green proof; that remains Part 6.

See [test strategy](../../docs/test-strategy.md) for commands, layers and limitations. One upstream TestClient/HTTPX deprecation warning remains; all tests passed.
