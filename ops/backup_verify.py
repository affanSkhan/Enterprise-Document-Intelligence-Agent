"""Verify that a SQLite/PostgreSQL backup target is reachable before deployment.

This intentionally does not perform destructive restore operations. Production restore drills
should run against an isolated database using the organization's backup tooling.
"""
import os
import sys

from sqlalchemy import create_engine, text


url = os.environ.get("DATABASE_URL")
if not url:
    print("DATABASE_URL is required")
    raise SystemExit(2)

engine = create_engine(url, pool_pre_ping=True)
with engine.connect() as connection:
    connection.execute(text("SELECT 1"))
print("Database connectivity verification passed; run an isolated restore drill separately.")
