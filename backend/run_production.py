from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    port = env.get("PORT", "10000")

    # Ingestion now uses a bounded in-process executor backed by durable
    # PostgreSQL jobs. Keeping a single Python runtime is important on
    # Render's 512 MB free instance; the old colocated Celery subprocess
    # pushed memory usage beyond the limit and caused 502s.
    return subprocess.call(
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


if __name__ == "__main__":
    raise SystemExit(main())
