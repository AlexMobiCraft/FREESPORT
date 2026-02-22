# Gemini Added Memories

- Отвечай и веди документацию исключительно на русском языке

# Command Validation Rules

- **CRITICAL**: Before executing any terminal command via `run_command`, verify that the `CommandLine` parameter:
  1. Starts with a valid command name (e.g., `docker`, `npm`, `python`, `git`) using only **Latin characters**
  2. Contains **NO Cyrillic characters** (like `с`, `а`, `о`, `е` which look similar to Latin `c`, `a`, `o`, `e`)
  3. Has **NO leading special characters or whitespace** before the command
- **PowerShell Chaining**: В среде Windows PowerShell для объединения команд используй `;` вместо `&&`. (Например: `git add .; git commit -m "..."; git push`).

# Terminal & SSH Rules (Anti-Hang)

- **Execution from Subdirectories**: Чтобы избежать зависаний терминала из-за индексации Git/Oh-My-Posh в корне проекта, ВСЕГДА запускай команды из подпапки (например, `scripts/` или `backend/`). Git автоматически найдет корень проекта.
- **SSH Authentication**: Используй только SSH-ключи через `ssh-agent`. Избегай интерактивных запросов пароля, так как они приводят к зависанию агента.
- **Production Git Updates**: При обновлении кода на продакшен-сервере НИКОГДА не используй `git pull`. ВСЕГДА используй: `git fetch origin main; git reset --hard origin/main`, чтобы избежать конфликтов и ошибки `divergent branches`.
- **Session Hygiene**: Если команды начинают выполняться медленно, используй опцию "Close Completely" при перезагрузке Antigravity, чтобы очистить зомби-процессы.
- **Command Shell**: Для простых системных задач (echo, dir, move) используй `cmd /c` вместо PowerShell, так как он запускается быстрее.

# Frontend Development Rules

- **CRITICAL**: After making changes to frontend code (`frontend/src/`), you **MUST** restart the Docker container before verifying the changes in browser:
  ```bash
  # Standard restart (for hot-reload issues)
  docker compose --env-file .env -f docker/docker-compose.yml restart frontend
  
  # Full rebuild (when dependencies or config changed)
  docker compose --env-file .env -f docker/docker-compose.yml up -d --build frontend
  ```
- This is required because the frontend runs in a Docker container and changes are not automatically reflected without restart.

# Backend Development & Testing

- **Testing via Docker**: ВСЕГДА запускай тесты бекенда внутри Docker-контейнера. Не пытайся использовать локальный `pytest` или `poetry run pytest`.
  Пример команды:
  `docker compose --env-file .env -f docker/docker-compose.yml exec -T backend pytest <путь_к_тесту>`

# Project Reference

Справочная информация о проекте (архитектура, стек, команды запуска и тесты) перенесена в отдельный файл:
👉 `docs/PROJECT_INFO.md`

Всегда обращайся к нему для понимания структуры проекта, но следуй правилам выше при выполнении команд.
