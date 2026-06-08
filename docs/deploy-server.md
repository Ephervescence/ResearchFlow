# Server Deployment Guide

This guide deploys ResearchFlow without Docker. It is designed for an Ubuntu server using:

- PostgreSQL + pgvector installed on the host
- FastAPI backend managed by systemd
- React + Vite frontend served by Nginx

## 1. Install System Dependencies

```bash
sudo apt update
sudo apt install -y git curl nginx python3 python3-venv python3-pip postgresql postgresql-contrib
```

Install Node.js with your preferred method. For example:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
node --version
npm --version
```

## 2. Install pgvector

On many Ubuntu/PostgreSQL setups, pgvector can be installed from packages:

```bash
sudo apt install -y postgresql-16-pgvector
```

If your PostgreSQL version is not 16, search the matching package:

```bash
apt search pgvector
```

If the package is unavailable, install pgvector from source according to the official pgvector
instructions.

## 3. Create Database and User

```bash
sudo -u postgres psql
```

Run:

```sql
CREATE DATABASE researchflow;
CREATE USER researchflow WITH PASSWORD 'change_me';
GRANT ALL PRIVILEGES ON DATABASE researchflow TO researchflow;
\c researchflow
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

## 4. Deploy Project Files

Clone or upload the project:

```bash
sudo mkdir -p /opt/researchflow
sudo chown "$USER":"$USER" /opt/researchflow
git clone <your-repo-url> /opt/researchflow
cd /opt/researchflow
git switch develop
```

## 5. Configure Backend

```bash
cd /opt/researchflow/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.server.example .env
nano .env
```

Set:

```env
DATABASE_URL=postgresql+psycopg://researchflow:change_me@localhost:5432/researchflow
CORS_ORIGINS=["https://your-domain.com"]
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-change-me
LLM_BASE_URL=https://api.deepseek.com
SEARCH_PROVIDER=ddgs
SEARCH_MAX_RESULTS=5
SEARCH_REGION=wt-wt
READER_TIMEOUT_SECONDS=15
READER_MAX_CHARS=6000
UPLOAD_DIR=/opt/researchflow/data/uploads
UPLOAD_MAX_BYTES=20971520
EMBEDDING_PROVIDER=mock
EMBEDDING_MODEL=mock-embedding-384
EMBEDDING_DIMENSIONS=384
CHUNK_MAX_CHARS=900
CHUNK_OVERLAP_CHARS=120
RAG_TOP_K=5
```

Test the backend manually:

```bash
alembic upgrade head
python scripts/check_database.py
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open another terminal:

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

Stop the manual server with `Ctrl+C`.

## 6. Create systemd Service

```bash
sudo nano /etc/systemd/system/researchflow-backend.service
```

Paste:

```ini
[Unit]
Description=ResearchFlow FastAPI Backend
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/researchflow/backend
EnvironmentFile=/opt/researchflow/backend/.env
ExecStart=/opt/researchflow/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Give the service user access to the project:

```bash
sudo mkdir -p /opt/researchflow/data/uploads
sudo chown -R www-data:www-data /opt/researchflow
```

Start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable researchflow-backend
sudo systemctl start researchflow-backend
sudo systemctl status researchflow-backend
```

View logs:

```bash
sudo journalctl -u researchflow-backend -f
```

## 7. Build Frontend

```bash
cd /opt/researchflow/frontend
npm install
cp .env.example .env
nano .env
```

For same-domain deployment, set:

```env
VITE_API_BASE_URL=/api
```

Build:

```bash
npm run build
```

## 8. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/researchflow
```

Paste and replace `your-domain.com`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /opt/researchflow/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/researchflow /etc/nginx/sites-enabled/researchflow
sudo nginx -t
sudo systemctl reload nginx
```

## 9. Optional HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 10. Update Deployment

```bash
cd /opt/researchflow
sudo -u www-data git pull

cd backend
sudo -u www-data .venv/bin/pip install -e .
sudo -u www-data .venv/bin/alembic upgrade head
sudo systemctl restart researchflow-backend

cd ../frontend
sudo -u www-data npm install
sudo -u www-data npm run build
sudo systemctl reload nginx
```

## Troubleshooting

Check backend status:

```bash
sudo systemctl status researchflow-backend
sudo journalctl -u researchflow-backend -n 100
```

Check database:

```bash
sudo -u postgres psql -d researchflow -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
cd /opt/researchflow/backend
sudo -u www-data .venv/bin/python scripts/check_database.py
```

Check Nginx:

```bash
sudo nginx -t
sudo tail -n 100 /var/log/nginx/error.log
```
