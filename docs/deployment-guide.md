# Deployment Guide — AWS EC2

Complete step-by-step guide to deploying the Task Manager API on AWS EC2.

---

## 1. EC2 Instance Setup

**Recommended:** Ubuntu 22.04 LTS, t3.micro (free tier eligible)

### Security Group Rules

| Type | Protocol | Port | Source |
|---|---|---|---|
| SSH | TCP | 22 | My IP (your IP only) |
| HTTP | TCP | 80 | 0.0.0.0/0 |
| HTTPS | TCP | 443 | 0.0.0.0/0 |

---

## 2. Server Provisioning — Install Docker

SSH into EC2 and run:

```bash
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

![UFW Firewall](screenshots/ufw-firewall.png)

---

## 4. fail2ban — SSH Brute-Force Protection

```bash
sudo apt install -y fail2ban

sudo tee /etc/fail2ban/jail.local << 'CONF'
[sshd]
enabled  = true
port     = ssh
maxretry = 5
bantime  = 3600
findtime = 600
CONF

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
sudo fail2ban-client status sshd
```

![fail2ban](screenshots/fail2ban.png)

---

## 5. Clone Repository + Configure Environment

```bash
git clone https://github.com/him1029g/task-manager-api.git ~/task-manager-api
cd ~/task-manager-api
```

![Git Clone](screenshots/gitclone-ec2.png)

```bash
cp .env.example .env
nano .env
```

Fill in your values:
```dotenv
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/dbname
REDIS_URL=rediss://default:token@hostname.upstash.io:6380
GEMINI_API_KEY=your_gemini_key
APP_ENV=production
ALLOWED_ORIGINS=
```

---

## 6. Generate SSL Certificate

```bash
chmod +x nginx/generate-ssl.sh
./nginx/generate-ssl.sh
ls -la nginx/ssl/
```

![NGINX SSL](screenshots/nginx-ssl.png)

---

## 7. Docker Login + Start Application

```bash
docker login
docker compose up -d
docker compose ps
```

![Docker Login](screenshots/docker-login-ec2.png)

![Docker Compose PS](screenshots/ec2-docker-ps.png)

![Docker Compose Running](screenshots/ece-docker-compose.png)

Verify health:
```bash
curl -k https://localhost/health
```

---

## 8. Automated Backups

```bash
chmod +x scripts/backup.sh
./scripts/backup.sh

# Add to crontab — daily at 2 AM UTC
crontab -e
# Add: 0 2 * * * /home/ubuntu/task-manager-api/scripts/backup.sh >> /home/ubuntu/backup.log 2>&1
```

![Taking Backup](screenshots/taking-backup.png)

![Backup Scripts](screenshots/backup_scripts.png)

---

## 9. GitHub Secrets Setup

Go to: **GitHub Repo → Settings → Secrets and variables → Actions**

| Secret | Value |
|---|---|
| `DOCKERHUB_USERNAME` | Your DockerHub username |
| `DOCKERHUB_TOKEN` | DockerHub → Account Settings → Security → Access Tokens |
| `EC2_HOST` | EC2 Public IP |
| `EC2_SSH_KEY` | Full content of your `.pem` key file |

---

## 10. CI/CD Pipeline Verification

Push to main or trigger manually from GitHub Actions tab.

![GitHub Actions 1](screenshots/github-action-1.png)

![GitHub Actions 2](screenshots/github-action-2.png)

![GitHub Actions 3](screenshots/github-action-3.png)

![GitHub Actions 4](screenshots/github-action-4.png)

**DockerHub — image pushed successfully:**

![DockerHub](screenshots/docker-hub-image.png)

---

## Data Persistence

| Data | Location on EC2 |
|---|---|
| PostgreSQL data | Docker volume `postgres_data` |
| Redis AOF data | Docker volume `redis_data` |
| Database backups | `/home/ubuntu/backups/db/` |
| SSL certificates | `~/task-manager-api/nginx/ssl/` |

```bash
# Inspect volumes
docker volume ls
docker volume inspect task-manager-api_postgres_data
```

---

## Cloud Services

### Neon — PostgreSQL
![Neon PostgreSQL](screenshots/cloud-postgres.png)

### Upstash — Redis
![Upstash Redis](screenshots/cloud-redis.png)

---

## Monitoring

```bash
# Health check script
~/health-check.sh
```

![Health Script](screenshots/ec2-health.sh.png)

```bash
# Application logs
docker logs task_api --tail 50
```

![Docker Logs](screenshots/ec2-docker-logs.png)

```bash
# Resource usage
docker stats --no-stream
```
