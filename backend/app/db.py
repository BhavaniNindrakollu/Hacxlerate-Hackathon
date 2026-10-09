from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import BACKEND_ROOT, get_settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def _engine_url() -> str:
    settings = get_settings()
    url = settings.database_url
    if url.startswith("sqlite:///./"):
        db_file = BACKEND_ROOT / url.replace("sqlite:///./", "", 1)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_file.as_posix()}"
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        db_file = Path_from_sqlite(url)
        if db_file:
            db_file.parent.mkdir(parents=True, exist_ok=True)
    return url


def Path_from_sqlite(url: str):
    from pathlib import Path

    raw = url.replace("sqlite:///", "", 1)
    path = Path(raw)
    return path


def get_engine() -> Engine:
    global _engine, SessionLocal
    if _engine is None:
        url = _engine_url()
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if SessionLocal is None:
        get_engine()
    assert SessionLocal is not None
    return SessionLocal


def reset_engine() -> None:
    global _engine, SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    SessionLocal = None


def migrate_schema(engine: Engine) -> None:
    """Add new tables and missing columns without dropping existing records."""
    from app import models  # noqa: F401 — register tables

    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "brands" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("brands")}
    statements: list[str] = []
    if "is_demo" not in columns:
        statements.append("ALTER TABLE brands ADD COLUMN is_demo BOOLEAN DEFAULT 0")
    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))


def init_db() -> None:
    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.backup_path.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    migrate_schema(engine)


def bootstrap_initial_admin() -> None:
    """Create the first administrator from env vars only when no users exist."""
    from app.models import User
    from app.security import hash_password, normalize_email, validate_password

    settings = get_settings()
    email = (settings.initial_admin_email or "").strip()
    password = settings.initial_admin_password or ""
    if not email or not password:
        return
    factory = get_session_factory()
    db = factory()
    try:
        if db.query(User).count() > 0:
            return
        try:
            validate_password(password, email)
        except ValueError:
            print("[ImpostorRadar] Initial admin password does not meet policy; skipping bootstrap.")
            return
        user = User(
            email=normalize_email(email),
            full_name="Administrator",
            password_hash=hash_password(password),
            role="administrator",
            is_active=True,
        )
        db.add(user)
        db.commit()
        print("[ImpostorRadar] Initial administrator account created from environment configuration.")
    except Exception as exc:
        db.rollback()
        print(f"[ImpostorRadar] Admin bootstrap error (non-fatal): {exc}")
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
