"""Show a deliberate validation bug and its repair in a disposable source copy."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = ROOT / "evid" / "04-tests"
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fulfillops-regression-") as directory:
        lab = Path(directory)
        for name in ("api", "common", "db"):
            shutil.copytree(
                ROOT / name, lab / name, ignore=shutil.ignore_patterns("__pycache__")
            )
        test = lab / "tests" / "unit"
        test.mkdir(parents=True)
        shutil.copyfile(
            ROOT / "tests/unit/test_quantity_regression.py",
            test / "test_quantity_regression.py",
        )
        shutil.copyfile(ROOT / "pytest.ini", lab / "pytest.ini")
        source = lab / "api/main.py"
        correct = source.read_text()
        before = "type(quantity) is not int"
        if correct.count(before) != 1:
            raise SystemExit(
                "Expected validation check changed; review demo before running"
            )
        buggy = correct.replace(before, "not isinstance(quantity, int)")
        env = {**os.environ, "PYTHONPATH": str(lab), "PYTHONDONTWRITEBYTECODE": "1"}
        command = [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_quantity_regression.py",
            "-v",
        ]
        for phase, content, expected in [("failing", buggy, 1), ("fixed", correct, 0)]:
            source.write_text(content)
            run = subprocess.run(
                command,
                check=False,
                cwd=lab,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = (
                "Deliberate regression demo in a disposable copy; working source and database unchanged.\n"
                "Bug: isinstance(True, int) accepts a boolean. Fix: use the strict integer type check.\n"
                "$ python -m pytest tests/unit/test_quantity_regression.py -v\n"
                + run.stdout
                + run.stderr
                + f"\nExit code: {run.returncode}\n"
            )
            (evidence / ("regression-" + phase + ".txt")).write_text(output)
            print(phase + ": exit " + str(run.returncode))
            if run.returncode != expected:
                raise SystemExit("Unexpected regression result; inspect saved output")
    print(
        "Expected failure followed by passing fix. Original source was never modified."
    )


if __name__ == "__main__":
    main()
