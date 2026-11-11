import os
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def settings():
    values = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if sep:
                parts = shlex.split(value, comments=True)
                values[key.strip()] = " ".join(parts)
    values.update(os.environ)
    return values
