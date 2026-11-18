# CashBuffer Self-Hosted Deployment Guide (Raspberry Pi & VPS)

Target platforms: Raspberry Pi 4/5 (Debian 12 / Raspberry Pi OS 64-bit arm64) or VPS (Ubuntu 22.04/24.04 amd64/arm64).

---

## 1. Prerequisites

- **OS:** Linux 64-bit (Debian, Ubuntu, Raspberry Pi OS 64-bit).
- **RAM:** Minimum 1GB RAM (swap file recommended on 1GB-2GB Pi).
- **Tools:** Docker (24.0+) & Docker Compose v2 (`docker compose`).
  ```bash
  # Install Docker on Debian/Ubuntu/Raspberry Pi OS:
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER
  ```

---

## 2. Configuration & Secrets

1. Clone repo and create environment configuration:
   ```bash
   cp .env.example .env
   ```

2. Generate secure encryption key & JWT secret:
   ```bash
   python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
   python3 -c "import secrets; print('LOCAL_JWT_SECRET=' + secrets.token_hex(32))"
   ```

3. Update `.env` with:
   - `ENCRYPTION_KEY`: Generated 32-byte Fernet key.
   - `LOCAL_JWT_SECRET`: Random 32+ byte string for local HS256 JWT tokens.
   - `TELEGRAM_BOT_TOKEN`: Token from [@BotFather](https://t.me/botfather).
   - `ALLOWED_ORIGINS`: Comma-separated domains for CORS (e.g. `https://cashbuffer.example.com`).
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: From Google Cloud Console.

4. Mount Gmail OAuth tokens for Ingress daemon:
   ```bash
   mkdir -p secrets
   # Copy credentials.json and token.json (generated via scripts/gmail_auth.py)
   cp credentials.json secrets/
   cp token.json secrets/
   ```

---

## 3. Launching Services

Start the microservices stack (PostgreSQL, Migration Runner, FastAPI Core, Ingress Worker, FastMCP):

```bash
docker compose up -d
```

Check logs and health status:
```bash
docker compose ps
docker compose logs -f migration
docker compose logs -f api
```

Health check endpoints:
- Core API: `http://localhost:8000/health`
- MCP Server: `http://localhost:8080/health`

---

## 4. Reverse Proxy & TLS (Caddy or Nginx)

Ports are bound to `127.0.0.1` by default to prevent exposing unencrypted HTTP or raw Postgres to public network. Terminate TLS with a reverse proxy.

### Option A: Caddy (Automatic HTTPS)

Install Caddy:
```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

`/etc/caddy/Caddyfile`:
```caddy
cashbuffer.example.com {
    # Core API
    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }
    handle /health {
        reverse_proxy 127.0.0.1:8000
    }

    # FastMCP Server (SSE transport)
    handle /mcp/* {
        reverse_proxy 127.0.0.1:8080
    }
}
```

Reload Caddy:
```bash
sudo systemctl reload caddy
```

---

## 5. Backups & Restore

### Automated Backup
Run backup script manually or via cron:
```bash
./scripts/backup_db.sh
```

Daily backup cron (`crontab -e`):
```cron
0 3 * * * cd /path/to/CashBuffer && ./scripts/backup_db.sh >> /var/log/cashbuffer_backup.log 2>&1
```

### Restore
```bash
./scripts/restore_db.sh backups/cashbuffer_cashbuffer_YYYYMMDD_HHMMSS.sql.gz
```

---

## 6. Raspberry Pi Optimization Notes

- **Memory Limits:** Containers in `docker-compose.yml` are capped (API: 200M, Ingress: 150M, MCP: 150M, DB: 200M) — total ~700MB, leaving ample headroom for OS on a 2GB Pi.
- **MicroSD Card Protection:** For longevity on microSD, redirect Docker logging to json-file with max size limits or mount `/var/lib/docker` on an external USB SSD.
- **ARM64 Architecture:** All container images (`python:3.11-slim`, `postgres:16-alpine`) natively support `linux/arm64`.
