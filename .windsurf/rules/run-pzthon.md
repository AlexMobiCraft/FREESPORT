---
trigger: always_on
description: запуск скриптов python
---

Пред запуском скриптов на python нужно убедиться что загружено виртуальное окружение, если не загружено выполнить загрузку виртуального окружения (backend\venv\Scripts\activate)

### **Docker**

The recommended way to run the project is with Docker Compose.

**Local Development:**

```bash
docker compose --env-file .env -f docker/docker-compose.yml
```

**Production:**

```bash
docker compose --env-file .env.prod -f docker/docker-compose.prod.yml
```
