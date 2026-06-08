# Windows Local PostgreSQL Setup

ResearchFlow does not require Docker. On Windows, use a native PostgreSQL installation.

## 1. Install PostgreSQL

Install PostgreSQL from the official Windows installer. During installation:

- Keep the default port `5432`.
- Remember the `postgres` superuser password.
- Install Stack Builder only if you need extra extensions.

After installation, make sure the PostgreSQL service is running from Windows Services.

## 2. Install pgvector

ResearchFlow requires the `vector` extension. If your PostgreSQL installer does not include
pgvector, install it using one of these approaches:

- Use Stack Builder if pgvector is available for your PostgreSQL version.
- Use a PostgreSQL distribution that bundles pgvector.
- Build/install pgvector manually following the pgvector project instructions.

You can verify whether pgvector is available inside `psql`:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

If PostgreSQL says the extension control file is missing, pgvector is not installed yet.

## 3. Create ResearchFlow Database

Open SQL Shell or pgAdmin as the `postgres` user and run:

```sql
CREATE DATABASE researchflow;
CREATE USER researchflow WITH PASSWORD 'researchflow';
GRANT ALL PRIVILEGES ON DATABASE researchflow TO researchflow;
\c researchflow
CREATE EXTENSION IF NOT EXISTS vector;
```

If you use pgAdmin instead of SQL Shell, switch to the `researchflow` database before running:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 4. Configure Backend

Create `backend/.env` from the example:

```powershell
Copy-Item backend/.env.example backend/.env
```

Confirm this line matches your local database:

```env
DATABASE_URL=postgresql+psycopg://researchflow:researchflow@localhost:5432/researchflow
```

## 5. Run Integration Check

From the project root:

```powershell
.\scripts\local-integration.ps1
```

Expected successful output includes:

- Python imports pass.
- Alembic migrations complete.
- pgvector is enabled.
- API smoke test prints counts for steps, sources, report, citations, and memories.

If it fails with `PostgreSQL is not reachable`, check:

- The PostgreSQL service is running.
- Port `5432` is not blocked.
- `DATABASE_URL` points to the right host, port, user, password, and database.
