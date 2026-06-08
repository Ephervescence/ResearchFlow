from sqlalchemy import text

from app.db.session import engine


REQUIRED_TABLES = {
    "tasks",
    "agent_steps",
    "sources",
    "notes",
    "uploaded_files",
    "document_chunks",
    "memories",
    "reports",
    "report_citations",
}


def main() -> None:
    with engine.connect() as connection:
        version = connection.execute(text("SELECT version()")).scalar_one()
        vector_enabled = connection.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        ).scalar_one()
        table_rows = connection.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
        ).scalars()
        tables = set(table_rows)

    missing = sorted(REQUIRED_TABLES - tables)
    print(f"PostgreSQL: {version}")
    print(f"pgvector enabled: {vector_enabled}")
    print(f"required tables present: {not missing}")
    if missing:
        print(f"missing tables: {', '.join(missing)}")
        raise SystemExit(1)
    if not vector_enabled:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
