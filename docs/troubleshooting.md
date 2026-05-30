# Troubleshooting Guide

---

## Container Issues

### Containers not starting
```bash
# Check status of all containers
docker compose ps

# View last 50 lines of logs
docker compose logs --tail 50

# Check specific service
docker logs task_api --tail 100
docker logs nginx_proxy --tail 100
```

### API container stuck in "starting" / unhealthy
```bash
# Check health check output
docker inspect task_api | grep -A 10 '"Health"'

# Manual health check inside the container
docker exec task_api curl -f http://localhost:8000/health

# Check if .env file exists and has required variables
docker exec task_api env | grep -E 'DATABASE_URL|REDIS_URL|GEMINI'
```

### NGINX fails to start
```bash
# Validate nginx config
docker run --rm -v $(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:1.25-alpine nginx -t

# Check if SSL certs exist
ls -la nginx/ssl/
# If missing, regenerate:
./nginx/generate-ssl.sh
```

---

## Database Issues

### "Connection refused" or SSL errors
```bash
# Verify DATABASE_URL format in .env
# Neon requires: postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require

# Test connection directly
docker exec task_api python -c "
import asyncio
from app.database import engine
from sqlalchemy import text
async def test():
    async with engine.connect() as c:
        r = await c.execute(text('SELECT version()'))
        print(r.scalar())
asyncio.run(test())
"
```

### Tables not created on startup
```bash
# Check startup logs for errors
docker logs task_api 2>&1 | grep -E 'startup|ERROR|CRITICAL'
```

---

## Redis Issues

### Redis connection errors
```bash
# Test Redis ping
docker exec task_api python -c "
import asyncio
from app.cache import get_redis
async def test():
    r = await get_redis()
    print(await r.ping())
asyncio.run(test())
"

# Upstash free tier note: connections drop after inactivity.
# The health_check_interval=30 setting in cache.py keeps it alive.
```

---

## CI/CD Issues

### Deploy job fails at health gate
```bash
# SSH into EC2 and check manually
docker compose ps
docker logs task_api --tail 50
docker inspect task_api | grep -A 5 '"Health"'

# If rollback happened, check what image is running
docker inspect task_api | grep Image
```

### "Permission denied" on scripts after deploy
```bash
# The deploy.yml runs chmod automatically, but you can also:
chmod +x scripts/backup.sh nginx/generate-ssl.sh
```

### SCP step fails — file not found
Ensure these files exist in the repository root (not gitignored):
- `docker-compose.yml`
- `nginx/nginx.conf`
- `scripts/backup.sh`
- `.env.example`

---

## Backup Issues

### `pg_dump` command not found
```bash
# Install PostgreSQL client on EC2
sudo apt install -y postgresql-client
```

### Backup fails with authentication error
```bash
# Check DATABASE_URL is correctly set in .env
grep DATABASE_URL /home/ubuntu/task-manager-api/.env

# Test pg_dump manually
source <(grep DATABASE_URL /home/ubuntu/task-manager-api/.env)
pg_dump "$DATABASE_URL" | head -5
```

---

## Useful Commands

```bash
# Restart a single service
docker compose restart api
docker compose restart nginx

# View resource usage
docker stats

# Enter a container shell
docker exec -it task_api bash
docker exec -it nginx_proxy sh

# Pull latest image manually
docker compose pull api && docker compose up -d --no-deps api

# Full restart (preserve volumes)
docker compose down && docker compose up -d

# Nuclear option — remove everything including volumes (DATA LOSS)
# docker compose down -v
```
