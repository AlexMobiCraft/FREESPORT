# Development Guide

## Overview

We follow a strict **Docker-first** development workflow. All services (Backend, Frontend, DB, Redis, Nginx) run inside containers. Do not install Node.js or Python on your host machine for running the project.

**Primary References:**
- [Local Docker Setup](../docs/deploy/LOCAL_DOCKER_SETUP.md) - Detailed setup guide.
- [Docker Quick Reference](../docs/deploy/DOCKER_QUICK_REFERENCE.md) - Cheat sheet for common commands.

## Prerequisites

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Git**
- **OpenSSL** (for generating certificates)

## Quick Start

1. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env if needed (passwords must match docker-compose.yml)
   ```

2. **Generate SSL Certs (Critical for Nginx)**
   ```bash
   # Linux/macOS
   ./scripts/server/create-ssl-certs.sh
   
   # Windows (PowerShell)
   .\scripts\server\create-ssl-certs.ps1
   ```

3. **Start Services**
   ```bash
   docker compose --env-file .env -f docker/docker-compose.yml up -d
   ```

4. **Initialize Backend**
   ```bash
   # Migrate DB
   docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py migrate
   
   # Collect Statics
   docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py collectstatic --no-input
   
   # Create Admin (Optional)
   docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py createsuperuser
   ```

## Workflow

### Frontend Development
Code changes in `frontend/src` are hot-reloaded automatically via the mounted volume.
- **Logs:** `docker compose --env-file .env -f docker/docker-compose.yml logs -f frontend`
- **Install Package:** 
  ```bash
  docker compose --env-file .env -f docker/docker-compose.yml exec frontend npm install <package>
  ```

### Backend Development
Code changes in `backend/` auto-restart Gunicorn/Django dev server.
- **Logs:** `docker compose --env-file .env -f docker/docker-compose.yml logs -f backend`
- **Shell:** `docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py shell`
- **Migrations:**
  ```bash
  docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py makemigrations
  docker compose --env-file .env -f docker/docker-compose.yml exec backend python manage.py migrate
  ```

## Testing

Run tests ONLY inside containers:

```bash
# Frontend Tests
docker compose --env-file .env -f docker/docker-compose.yml exec frontend npm test

# Backend Tests
docker compose --env-file .env -f docker/docker-compose.yml exec backend pytest
```

## Access Points

- **Frontend:** https://localhost (via Nginx) or http://localhost:3000 (Direct)
- **API:** https://localhost/api/v1 (via Nginx) or http://localhost:8001/api/v1 (Direct)
- **Admin:** https://localhost/admin/
- **Swagger:** https://localhost/api/schema/swagger-ui/

## Troubleshooting

- **SSL Errors:** Ensure you ran the cert generation script. Restart Nginx: `docker compose ... restart nginx`.
- **Permission Errors:** On Linux, check volume permissions.
- **Container Conflicts:** `docker compose ... down -v` to wipe clean.