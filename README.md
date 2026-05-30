# Task Manager API

> **DevOps Assignment** — A production-grade FastAPI application demonstrating real-world DevOps practices: containerised with Docker, deployed on AWS EC2, secured behind NGINX with TLS, backed by managed cloud services, and delivered via a GitHub Actions CI/CD pipeline.

**Demo Video Part 1 :** [Watch on Loom](https://www.loom.com/share/52c8c9a60285431cba02cc2dab9013e8)

**Demo Video Part 2 :** [Watch on Loom](https://www.loom.com/share/8267eda7a60f44779f8e726cf26ca73b)

---

## Live Screenshots

### Application Running on AWS EC2

![Home Page](docs/screenshots/ec2-ip-home-page.png)

![Home Page with Tasks](docs/screenshots/ec2-ip-home-page-2.png)

### Gemini AI Summary

![AI Summary](docs/screenshots/ec2-ip-gen-ai.png)

### Health Check — All Dependencies OK

![Health Check](docs/screenshots/ec2-ip-health-check.png)

### Swagger API Docs

![Swagger UI](docs/screenshots/ec2-ip-swagger.png)

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
| API Framework | FastAPI + Uvicorn (2 workers) |
| Database | PostgreSQL via Neon (managed, SSL) |
| Cache | Redis via Upstash (managed, TLS) |
| AI | Google Gemini 2.5 Flash |
| Reverse Proxy | NGINX 1.25-alpine |
| Containerisation | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Hosting | AWS EC2 (t3.micro, Ubuntu 22.04) |
| TLS | Self-signed (Let's Encrypt ready) |

---

## Project Structure

![Folder Structure](docs/screenshots/folder-structure.png)

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
│       ├── health.py    # GET /health — DB + Redis latency check
│       ├── tasks.py     # CRUD /tasks/* with Redis caching
│       └── ai.py        # GET /ai/summary (Gemini 2.5 Flash)
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
│   ├── troubleshooting.md
│   └── screenshots/     # All deployment screenshots
├── .github/workflows/
│   └── deploy.yml       # CI/CD pipeline
├── Dockerfile           # Multi-stage build
├── docker-compose.yml   # Production + local dev profiles
├── requirements.txt
├── .env.example
└── .gitignore
```

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
# Edit .env — for local dev use these values:
#   DATABASE_URL=postgresql://taskuser:taskpass@postgres:5432/taskdb
#   REDIS_URL=redis://redis:6379

# 3. Start all services (including local postgres + redis)
docker compose --profile local up -d --build

# 4. Check health
curl http://localhost/health
```

**Local Docker running:**

![Local Docker](docs/screenshots/local-docker.png)

![Localhost Health](docs/screenshots/localhost-health.png)

---

## Production Deployment

See **[docs/deployment-guide.md](docs/deployment-guide.md)** for the complete step-by-step EC2 guide.

### EC2 Setup Summary

**Clone & configure on EC2:**
```bash
git clone https://github.com/him1029g/task-manager-api.git ~/task-manager-api
cd ~/task-manager-api
cp .env.example .env && nano .env
./nginx/generate-ssl.sh
docker compose up -d
```

![Git Clone on EC2](docs/screenshots/gitclone-ec2.png)

**NGINX SSL certificate generated:**

![NGINX SSL](docs/screenshots/nginx-ssl.png)

**Docker running on EC2:**

![EC2 Docker Compose PS](docs/screenshots/ec2-docker-ps.png)

![EC2 Docker Compose](docs/screenshots/ece-docker-compose.png)

**FastAPI running on EC2:**

![FastAPI EC2](docs/screenshots/fast-api-ec2.png)

---

## CI/CD Pipeline

```
git push → main
      │
      ├─ Job 1: Build & Push
      │    ├── docker/setup-buildx-action
      │    ├── docker/login-action (DockerHub)
      │    └── docker/build-push-action
      │         ├── tags: :latest + :<commit-sha>
      │         └── BuildKit layer cache (registry)
      │
      └─ Job 2: Deploy to EC2
           ├── SCP: sync docker-compose.yml, nginx.conf, scripts
           ├── SSH: docker compose pull api
           ├── SSH: docker compose up -d --no-deps api
           ├── Health gate: 12 × 5s retries → auto rollback on failure
           ├── nginx -s reload
           └── docker image prune -f
```

### GitHub Actions — Pipeline Screenshots

![GitHub Actions 1](docs/screenshots/github-action-1.png)

![GitHub Actions 2](docs/screenshots/github-action-2.png)

![GitHub Actions 3](docs/screenshots/github-action-3.png)

![GitHub Actions 4](docs/screenshots/github-action-4.png)

### DockerHub Image

![DockerHub Image](docs/screenshots/docker-hub-image.png)

**Required GitHub Secrets**

| Secret | Value |
|---|---|
| `DOCKERHUB_USERNAME` | Your DockerHub username |
| `DOCKERHUB_TOKEN` | DockerHub access token |
| `EC2_HOST` | EC2 public IP or hostname |
| `EC2_SSH_KEY` | Private SSH key (PEM, no passphrase) |

---

## Cloud Services

### PostgreSQL — Neon

![Neon PostgreSQL](docs/screenshots/cloud-postgres.png)

### Redis — Upstash

![Upstash Redis](docs/screenshots/cloud-redis.png)

---

## Security

- NGINX terminates TLS (TLS 1.2/1.3 only, strong cipher suite)
- FastAPI is **not** exposed directly — only NGINX ports 80/443 are open
- Rate limiting: 30 req/min per IP, burst 10 (`limit_req_zone`)
- Security headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- `server_tokens off` — NGINX version hidden from responses
- All containers run as non-root (`appuser` UID 1001)
- `no-new-privileges:true` on all containers
- API container runs with read-only root filesystem
- Secrets in `.env` file — never committed to git

### UFW Firewall

![UFW Firewall](docs/screenshots/ufw-firewall.png)

### fail2ban — SSH Protection

![fail2ban](docs/screenshots/fail2ban.png)

### Docker Login on EC2

![Docker Login EC2](docs/screenshots/docker-login-ec2.png)

---

## Logging & Monitoring

Application logs are structured and captured by Docker:

```
2026-05-30T10:32:01 | INFO     | app.routers.tasks | cache | MISS tasks:all — querying DB
2026-05-30T10:32:01 | INFO     | app.routers.tasks | tasks | created id=1 title='Deploy app'
```

**View logs:**
```bash
docker logs task_api -f --tail 100
docker logs nginx_proxy -f --tail 100
docker exec nginx_proxy tail -f /var/log/nginx/access.log
```

### EC2 Docker Logs

![EC2 Docker Logs](docs/screenshots/ec2-docker-logs.png)

### Health Check Script

![Health Script](docs/screenshots/ec2-health.sh.png)

Log rotation configured via Docker `json-file` driver (`max-size: 10m`, `max-file: 5`).

---

## Backup & Recovery

```bash
# Manual backup
./scripts/backup.sh

# Automated — daily at 2 AM UTC
crontab -e
# 0 2 * * * /home/ubuntu/task-manager-api/scripts/backup.sh >> /home/ubuntu/backup.log 2>&1

# Restore
gunzip -c /home/ubuntu/backups/db/taskdb_YYYYMMDD_HHMMSS.sql.gz | psql "$DATABASE_URL"
```

Backups stored in `/home/ubuntu/backups/db/` — retained for 7 days.

### Backup Running

![Taking Backup](docs/screenshots/taking-backup.png)

![Backup Scripts](docs/screenshots/backup_scripts.png)

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

## Documentation

| Doc | Description |
|---|---|
| [Deployment Guide](docs/deployment-guide.md) | Full EC2 setup — Docker, UFW, fail2ban, SSL, cron |
| [SSL Upgrade Guide](docs/ssl-upgrade.md) | Migrate from self-signed to Let's Encrypt |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and debug commands |

