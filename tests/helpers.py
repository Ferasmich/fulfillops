import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager

import httpx

from common.config import ROOT


@contextmanager
def server():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ],
        cwd=ROOT,
        env=os.environ.copy(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        with httpx.Client(timeout=5) as http:
            for _ in range(100):
                if process.poll() is not None:
                    raise AssertionError("API subprocess exited before readiness")
                try:
                    if http.get(url + "/health/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.05)
            else:
                raise AssertionError("API did not become ready")
        yield url, process.pid
    finally:
        process.terminate()
        process.wait(timeout=10)
