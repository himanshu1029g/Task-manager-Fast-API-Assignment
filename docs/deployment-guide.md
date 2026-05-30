# Deployment Guide — AWS EC2

Step-by-step guide to deploying the Task Manager API on a fresh AWS EC2 instance.

---

## 1. EC2 Instance Setup

**Recommended:** Ubuntu 22.04 LTS, t3.micro (free tier eligible)

### Security Group Rules

| Type | Protocol | Port | Source |
|---|---|---|---|
| SSH | TCP | 22 | Your IP only |
| HTTP | TCP | 80 | 0.0.0.0/0 |
| HTTPS | TCP | 443 | 0.0.0.0/0 |

---

## 2. Server Provisioning

SSH into your EC2 instance and run the following:

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Allow ubuntu user to run Docker without sudo
sudo usermod -aG docker ubuntu
newgrp docker

# Install PostgreSQL client (for backups)
sudo apt install -y postgresql-client

# Verify
docker --version
docker compose version
```

---

## 3. UFW Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw enable
sudo ufw status verbose
```

---

## 4. fail2ban (SSH Brute-Force Protection)

```bash
sudo apt install -y fail2ban

sudo tee /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled  = true
port     = ssh
maxretry = 5
bantime  = 3600
findtime = 600
EOF

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
sudo fail2ban-client status sshd
```

---

## 5. Clone the Repository

```bash
git clone https://github.com/him1029g/task-manager-api.git ~/task-manager-api
cd ~/task-manager-api
```

---

## 6. Configure Environment

```bash
cp .env.example .env
nano .env
```

Fill in:
- `DATABASE_URL` — your Neon PostgreSQL connection string
- `REDIS_URL` — your Upstash Redis connection string
- `GEMINI_API_KEY` — your Google Gemini API key

---

## 7. Generate SSL Certificate

```bash
chmod +x nginx/generate-ssl.sh
./nginx/generate-ssl.sh
# Certificate created at nginx/ssl/cert.pem and nginx/ssl/key.pem
```

---

## 8. Start the Application

```bash
# Pull the image and start services
docker compose up -d

# Watch startup logs
docker compose logs -f

# Verify health
curl -k https://localhost/health
```

Expected response:
```json
{
  "status": "healthy",
  "dependencies": {
    "database": {"status": "ok", "latency_ms": 45.2},
    "redis":    {"status": "ok", "latency_ms": 12.1}
  }
}
```

---

## 9. Set Up Automated Backups

```bash
chmod +x scripts/backup.sh

# Test the backup script manually
./scripts/backup.sh

# Add to crontab — runs daily at 2:00 AM UTC
crontab -e
```

Add this line:
```
0 2 * * * /home/ubuntu/task-manager-api/scripts/backup.sh >> /home/ubuntu/backup.log 2>&1
```

---

## 10. Configure GitHub Actions

In your GitHub repository, go to **Settings → Secrets and variables → Actions** and add:

| Secret | Where to get it |
|---|---|
| `DOCKERHUB_USERNAME` | Your DockerHub username |
| `DOCKERHUB_TOKEN` | DockerHub → Account Settings → Security → Access Tokens |
| `EC2_HOST` | EC2 Public IP (from AWS Console) |
| `EC2_SSH_KEY` | Content of your EC2 `.pem` key file |

Also create an **Environment** named `production` in GitHub (Settings → Environments).

Test the pipeline by pushing to `main` or triggering manually from the Actions tab.

---

## Data Persistence

| Data | Storage Location on EC2 |
|---|---|
| PostgreSQL data | Docker volume `postgres_data` → `/var/lib/docker/volumes/task-manager-api_postgres_data/` |
| Redis AOF data | Docker volume `redis_data` → `/var/lib/docker/volumes/task-manager-api_redis_data/` |
| Database backups | `/home/ubuntu/backups/db/` |
| SSL certificates | `~/task-manager-api/nginx/ssl/` |

Volumes survive `docker compose down` and container recreation. To inspect:
```bash
docker volume ls
docker volume inspect task-manager-api_postgres_data
```
