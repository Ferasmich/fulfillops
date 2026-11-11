# Part 4 — Testing notes

The tests are now split into unit, integration and concurrency layers. This makes it easier to see whether a failure is in input rules, database behavior or coordination between processes.

There are 52 passing cases: 17 unit, 26 API integration, seven worker/checker and two dedicated races. The full supplied checker also passed 15 checks with no skips. The earlier combined race was replaced with two independent tests so each scenario starts with fresh stock.

The deliberate bug demo uses a temporary code copy. Changing the quantity check to `isinstance(quantity, int)` allows `True` through because Python's bool is a subclass of int. The test expects INVALID_QUANTITY, so it fails. Restoring `type(quantity) is not int` makes the same test pass. Both outputs are saved.

## Questions to prepare for

- **Unit versus integration?** A unit test checks a rule without the database. An integration test checks that the API and database work together.
- **Why two race tests?** Same-key requests test duplicate prevention; different keys test competition for limited stock.
- **Why two API processes?** An in-memory lock could pass in one process and fail across replicas. Both processes must share the database protections.
- **What does the barrier do?** It holds clients until they are ready, then lets them issue requests together.
- **Does a green checker mean the whole project is finished?** No. CI, security, containers, GitOps and operational evidence are separate requirements.
- **Why keep the failing output?** It shows the test actually detects the deliberately introduced bug rather than only passing on correct code.
- **Was the bug put into the live API?** No. The reproducible exercise runs against a disposable code copy, which is explained in the evidence.

The next main step is Part 5: package the API and worker in non-root Docker images and run the complete local stack with Compose.
