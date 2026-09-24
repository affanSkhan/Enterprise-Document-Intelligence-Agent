"""Render production entrypoint for the repository-root service configuration.

Render currently invokes this module from the repository root. Keep the actual
FastAPI application under backend/app while making the production command
portable across Render and local execution.
"""

from __future__ import annotations

import os
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import uvicorn  # noqa: E402


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
