# Task Manager API

A production-grade FastAPI application demonstrating DevOps best practices — containerised with Docker, deployed on AWS EC2, secured behind NGINX with TLS, backed by managed cloud services, and delivered via a GitHub Actions CI/CD pipeline.

---

## Architecture Overview

```
Internet
   │
   ▼
[AWS EC2 — Ubuntu 22.04]
   │
   ├─ UFW (ports 22, 80, 443 only)
   │
   ▼
[Docker Network: app_net 172.20.0.0/24]
   │
   ├── nginx:1.25-alpine  (ports 80 → 443, TLS termination, rate limiting)
   │         │
   │         └── proxy_pass → http://api:8000
   │
   ├── task_api (FastAPI + Uvicorn, 2 workers, non-root user)
   │         │
   │         ├── PostgreSQL  ──► Neon (managed, SSL)
   │         └── Redis       ──► Upstash (managed, TLS)
   │
   └── [local profile only]
             ├── postgres:15-alpine  (volume: postgres_data)
             └── redis:7-alpine      (volume: redis_data, AOF)
```

**Tech Stack**

| Layer | Technology |
|---|---|
| API Framework | FastAPI 0.111 + Uvicorn |
| Database | PostgreSQL via Neon (managed) |
| Cache | Redis via Upstash (managed, TLS) |
| AI | Google Gemini 1.5 Flash |
| Reverse Proxy | NGINX 1.25-alpine |
| Containerisation | Docker + Docker Compose 3.9 |
| CI/CD | GitHub Actions |
| Hosting | AWS EC2 (t3.micro, Ubuntu 22.04) |
| TLS | Self-signed (Let's Encrypt ready) |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check — DB, Redis, latency |
| GET | `/tasks/` | List all tasks (Redis cached, 60s TTL) |
| POST | `/tasks/` | Create a task |
| GET | `/tasks/{id}` | Get task by ID |
| PATCH | `/tasks/{id}` | Update task fields |
| DELETE | `/tasks/{id}` | Delete task |
| GET | `/ai/summary` | Gemini AI workload summary |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc UI |
| GET | `/` | Frontend dashboard |

---

## Quick Start — Local Development

```bash
# 1. Clone the repo
git clone https://github.com/him1029g/task-manager-api.git
cd task-manager-api

# 2. Set up environment
cp .env.example .env
# Edit .env — for local dev use the values below:
#   DATABASE_URL=postgresql://taskuser:taskpass@postgres:5432/taskdb
#   REDIS_URL=redis://redis:6379

# 3. Start all services (including local postgres + redis)
docker compose --profile local up -d

# 4. Check health
curl http://localhost/health
```

---

## Production Deployment

See **[docs/deployment-guide.md](docs/deployment-guide.md)** for the full step-by-step EC2 setup.

Quick summary:
```bash
# On EC2 — first-time setup
git clone https://github.com/him1029g/task-manager-api.git ~/task-manager-api
cd ~/task-manager-api
cp .env.example .env && nano .env          # Fill in production values
./nginx/generate-ssl.sh                    # Generate self-signed TLS cert
docker compose up -d                       # Start api + nginx
```

Subsequent deployments are handled automatically by GitHub Actions on every push to `main`.

---

## CI/CD Pipeline

```
git push → main
      │
      ├─ Job 1: Build & Push
      │    ├── docker/setup-buildx-action
      │    ├── docker/login-action (DockerHub)
      │    └── docker/build-push-action
      │         ├── tags: :latest + :<sha>
      │         └── BuildKit layer cache (registry)
      │
      └─ Job 2: Deploy to EC2
           ├── SCP: sync docker-compose.yml, nginx.conf, scripts
           ├── SSH: docker compose pull api
           ├── SSH: docker compose up -d --no-deps api
           ├── Health gate: 12 × 5s retries → rollback on failure
           ├── nginx -s reload (picks up any config changes)
           └── docker image prune -f
```

**Required GitHub Secrets**

| Secret | Value |
|---|---|
| `DOCKERHUB_USERNAME` | Your DockerHub username |
| `DOCKERHUB_TOKEN` | DockerHub access token |
| `EC2_HOST` | EC2 public IP or hostname |
| `EC2_SSH_KEY` | Private SSH key (PEM, no passphrase) |

---

## Security

- NGINX terminates TLS (TLS 1.2/1.3 only, strong cipher suite)
- FastAPI is **not** exposed directly — only NGINX ports 80/443 are open
- Rate limiting: 30 req/min per IP, burst 10 (`limit_req_zone`)
- Security headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- `server_tokens off` — NGINX version hidden
- All containers run as non-root (`appuser` UID 1001)
- `no-new-privileges:true` on all containers
- API container runs with read-only root filesystem (`read_only: true`)
- Secrets managed via `.env` file — never committed to git
- UFW: only ports 22, 80, 443 allowed (see deployment guide)
- fail2ban: SSH brute-force protection (see deployment guide)

---

## Logging

Application logs are written to stdout in structured format and captured by Docker:

```
2024-05-30T14:32:01 | INFO     | app.routers.tasks | cache | MISS tasks:all — querying DB
2024-05-30T14:32:01 | INFO     | app.routers.tasks | tasks | created id=42 title='Deploy app'
```

**View logs:**
```bash
docker logs task_api -f --tail 100      # FastAPI logs
docker logs nginx_proxy -f --tail 100   # NGINX access/error logs

# NGINX access log on EC2 (inside container)
docker exec nginx_proxy tail -f /var/log/nginx/access.log
```

Log rotation is configured via Docker's `json-file` driver (`max-size: 10m`, `max-file: 5`).

---

## Backup & Recovery

```bash
# Manual backup
./scripts/backup.sh

# Automated — add to crontab (daily at 2 AM UTC):
crontab -e
# 0 2 * * * /home/ubuntu/task-manager-api/scripts/backup.sh >> /home/ubuntu/backup.log 2>&1

# Restore from backup
gunzip -c /home/ubuntu/backups/db/taskdb_YYYYMMDD_HHMMSS.sql.gz | psql "$DATABASE_URL"
```

Backups are stored in `/home/ubuntu/backups/db/` and retained for 7 days.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `APP_ENV` | — | `production` (default) or `development` |
| `ALLOWED_ORIGINS` | — | Comma-separated CORS origins. Blank = allow all |

---

## Project Structure

```
task-manager-api/
├── app/
│   ├── main.py          # App init, CORS, lifespan, exception handler
│   ├── config.py        # Pydantic settings from env vars
│   ├── database.py      # Async SQLAlchemy engine + session
│   ├── cache.py         # Redis async client
│   ├── models.py        # SQLAlchemy Task model
│   ├── schemas.py       # Pydantic request/response schemas
│   └── routers/
│       ├── health.py    # GET /health
│       ├── tasks.py     # CRUD /tasks/*
│       └── ai.py        # GET /ai/summary (Gemini)
├── nginx/
│   ├── nginx.conf       # Reverse proxy, TLS, security headers, rate limiting
│   ├── generate-ssl.sh  # Self-signed cert generator
│   └── ssl/             # Cert files (gitignored)
├── scripts/
│   └── backup.sh        # PostgreSQL backup with retention
├── static/
│   └── index.html       # Frontend dashboard
├── docs/
│   ├── deployment-guide.md
│   ├── ssl-upgrade.md
│   └── troubleshooting.md
├── .github/workflows/
│   └── deploy.yml       # CI/CD pipeline
├── Dockerfile           # Multi-stage build
├── docker-compose.yml   # Production + local profiles
├── requirements.txt
├── .env.example
└── .gitignore
```
