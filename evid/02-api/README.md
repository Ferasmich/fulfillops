# Part 2 results

Tested on 10 November 2026 using Python 3.12.3 and the local PostgreSQL 16 Docker service.

- [Test output](test-results.txt): Ruff passed; 27 integration cases passed. Includes two API process IDs, same-key and competing-key results, and restart persistence.
- [JUnit results](test-results.xml): machine-readable test results.
- [Local database](database.txt): applied migration versions and seeded catalog, queried after migration.

Reproduce with `python -m pytest tests/integration/test_api.py -v -s`. Tests create and remove their own uniquely named database; they do not reset the working database. One upstream TestClient/HTTPX deprecation warning is recorded in the output.

The tests cover acceptance, replay, atomic reservation, validation and API restart persistence. Worker completion and the full supplied checker are not claimed. See `docs/part2-notes.md` for explanations and remaining work.
