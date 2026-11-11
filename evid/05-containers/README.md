# Part 5 evidence

Verified on 11 November 2026.

- [Build and Compose verification](compose-verification.txt): clean optimized/baseline builds; healthy API/two workers/database; non-root and restricted grants; shutdown/startup persistence and replay; guarded reset and private test cleanup.
- [Image sizes](image-sizes.json): runtime 192,614,009 bytes; baseline 264,756,846 bytes; about 27.2% smaller.
- [Container checker](public-checker.txt): **15 passed / 0 failed / 0 skipped**.
- [Default local stack](local-stack.txt): healthy services; init exited successfully.
- [Regression output](test-results.txt) and [JUnit](test-results.xml): **58 passed**, one upstream deprecation warning.
- [Static/unit checks](unit-and-static.txt): Ruff/formatting and 23 unit cases passed.

Repeat with `python -m scripts.verify_containers` after installing development requirements. It uses separate ports and a uniquely named project/volume, never resets the working dataset, and deletes only its own private test resources. Old failed build logs describe the Docker startup problem; successful clean builds are in `compose-verification.txt`.

[Report notes](../../docs/part5-notes.md) explain the design and fresh default-volume limitation. No registry publication or CI claim is made.
