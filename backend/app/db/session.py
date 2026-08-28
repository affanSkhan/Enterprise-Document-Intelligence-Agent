from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


def _normalize_database_url(url: str) -> str:
    """Prefer psycopg 3 for PostgreSQL even when the platform supplies a legacy URL."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


database_url = _normalize_database_url(settings.DATABASE_URL)
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _add_column_if_missing(conn, table: str, column: str, ddl: str) -> None:
    inspector = inspect(conn)
    columns = {c["name"] for c in inspector.get_columns(table)}
    if column not in columns:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def init_db() -> None:
    from app.db.models import Base
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        inspector = inspect(conn)
        if "users" in inspector.get_table_names():
            _add_column_if_missing(conn, "users", "password_hash", "VARCHAR(255)")
        if "jobs" in inspector.get_table_names():
            _add_column_if_missing(conn, "jobs", "idempotency_key", "VARCHAR(128)")
            _add_column_if_missing(conn, "jobs", "checkpoint", "VARCHAR(40) DEFAULT 'uploaded'")
            _add_column_if_missing(conn, "jobs", "attempts", "INTEGER DEFAULT 0")
            _add_column_if_missing(conn, "jobs", "max_attempts", "INTEGER DEFAULT 5")
            _add_column_if_missing(conn, "jobs", "available_at", "TIMESTAMP")


def bootstrap_admin() -> None:
    if not settings.ENABLE_AUTH or not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD or not settings.ADMIN_TENANT_ID:
        return
    from app.db.models import Tenant, User
    from app.security.auth import hash_password
    db = SessionLocal()
    try:
        tenant = db.get(Tenant, settings.ADMIN_TENANT_ID)
        if not tenant:
            tenant = Tenant(id=settings.ADMIN_TENANT_ID, name=settings.ADMIN_TENANT_NAME or settings.ADMIN_TENANT_ID)
            db.add(tenant)
            db.flush()
        user = db.query(User).filter(User.tenant_id == tenant.id, User.email == settings.ADMIN_EMAIL).first()
        if not user:
            db.add(User(tenant_id=tenant.id, email=settings.ADMIN_EMAIL, password_hash=hash_password(settings.ADMIN_PASSWORD), role="admin", is_active=True))
        else:
            # Keep the database credential synchronized with the explicitly
            # configured deployment secret. Previously existing users kept an
            # old hash forever, causing valid Render ADMIN_PASSWORD values to
            # fail with 401 after redeployments or environment changes.
            user.password_hash = hash_password(settings.ADMIN_PASSWORD)
            user.role = "admin"
            user.is_active = True
        db.commit()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
