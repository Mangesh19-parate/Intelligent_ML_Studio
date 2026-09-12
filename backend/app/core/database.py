from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

db_url = settings.sync_database_url

if db_url.startswith("sqlite"):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def sync_database_schema(engine_instance=engine) -> None:
    """
    Optional development-only helper for SQLite local iterations.
    In production/PostgreSQL, all schema modifications are strictly managed via Alembic migrations.
    """
    if not str(engine_instance.url).startswith("sqlite"):
        return
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine_instance)
        existing_tables = set(inspector.get_table_names())
        with engine_instance.connect() as conn:
            for table_name, table in Base.metadata.tables.items():
                if table_name in existing_tables:
                    existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
                    for col in table.columns:
                        if col.name not in existing_cols:
                            col_type = col.type.compile(engine_instance.dialect)
                            default_clause = ""
                            if col.default is not None and hasattr(col.default, "arg") and isinstance(col.default.arg, (int, float, str, bool)):
                                default_val = f"'{col.default.arg}'" if isinstance(col.default.arg, str) else str(col.default.arg)
                                default_clause = f" DEFAULT {default_val}"
                            sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{default_clause}"
                            conn.execute(text(sql))
            conn.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Development schema synchronization notice: {e}")

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

