from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    port = env.get("PORT", "10000")

    worker = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "app.worker.celery_app:celery_app",
            "worker",
            "--loglevel=INFO",
            "--pool=solo",
            "--concurrency=1",
            "-Q",
            "document-ingestion",
        ],
        cwd=ROOT,
        env=env,
    )

    try:
        api = subprocess.call(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                port,
            ],
            cwd=ROOT,
            env=env,
        )
    finally:
        if worker.poll() is None:
            worker.send_signal(signal.SIGTERM)
            try:
                worker.wait(timeout=15)
            except subprocess.TimeoutExpired:
                worker.kill()
    return api


if __name__ == "__main__":
    raise SystemExit(main())
