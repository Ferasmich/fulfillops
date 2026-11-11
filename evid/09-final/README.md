# Final verification and submission artifacts

The final clean-checkout run passed on 11 November 2026. Source snapshot: `0f8a7a9d18e4e94950e8bd3b6a9e562b89145017`. Later changes in this audit are documentation/report only; the Kubernetes setup guide was corrected to reference the deployed image.

- [Fresh environment/build/stack transcript](clean-checkout.txt): tracked source extracted into a new temporary directory, no copied .env/venv/volume, fresh pinned packages, pip check, lint/format, build and private Compose stack. Generated credentials are not logged.
- [Tests](tests.txt), [JUnit](tests.xml): **74 passed**, one upstream warning. Worker crash, poison job and both host-process races ran again against a disposable test database.
- [Final checker](public-checker.txt): **15 passed / 0 failed / 0 skipped**, both flags, fresh isolated Compose data.
- [Failing regression](regression-failing.txt), [fixed regression](regression-fixed.txt), [demo result](regression-demo.txt): reproduced in a temporary source copy.
- [Restart persistence](compose-persistence.json): 15 test orders/receipts, stock and totals identical across full down/up with the private volume retained. Cleanup then removed only that verification stack and volume.
- [Runtime user](runtime-user.txt), [image ID](local-image-id.txt), [summary](verification.json).
- [Eight-page report](FulfillOps-report.pdf), [editable report text](report.md).
- [Application CI artifact references](application-ci-artifacts.json): candidate run 43084811974 was successful. New artifact download attempts returned HTTP 502; the earlier downloaded CI SBOM/scan evidence is retained in Part 6.
- [Latest CI state at audit](latest-ci-status.json), [job list](pending-ci-jobs.json): evidence commit 0f8a7a9 remained queued with no jobs. Do not present this snapshot as a passed final workflow.

[Final requirement audit](../../docs/final-audit.md) separates completed technical proof from remaining presentation/submission actions. [Solo presentation script and timing](../../docs/presentation-runbook.md) is ready: 12 slides, planned 13:30 inside the 15-minute limit. The Canva deck is created for Feras MICHAEL; the approved accuracy corrections are saved.

## Reproduce

Use a new clone and follow README: create local .env with separate passwords; create the Python environment and install development requirements; start Compose; run pytest (its own disposable database); run the supplied checker with --concurrency --stress only once against fresh stock. Preserve data for down/up persistence. Never reset the retained Kubernetes database to make a checker rerun pass.

The checker transcript is ready for the requested grading screenshot. Capture the full 15 PASS lines and final 15/0/0 result in your VS Code terminal; do not include .env or credentials. A terminal screenshot could not be captured automatically because computer access to Terminal is restricted. Do not substitute a fabricated terminal image.
