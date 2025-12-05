---
description: Activates the DevOps Infrastructure Specialist Platform Engineer agent from the BMad Method.
---

---

<!-- Powered by BMAD™ Core -->

# infra-devops-platform

Workflow для подготовки и сопровождения инфраструктуры FREESPORT: от проверки окружения до обновления CI/CD и мониторинга. Все команды запускать в PowerShell (Windows) с учетом корпоративных правил (см. `docs/architecture/coding-standards.md`).

# Назначение

- Единый сценарий для DevOps-инженеров платформы
- Упорядоченный чек-лист для операций с инфраструктурой и пайплайнами
- Минимизация рисков при изменениях в продакшене

# Предусловия

1. Доступ к репозиторию и GitHub Actions Secrets
2. Авторизация в облачных провайдерах/серверах (SSH ключи, VPN)
3. Настроенный PowerShell и возможность запускать скрипты (`Set-ExecutionPolicy RemoteSigned`)
4. Загрузка виртуального окружения перед Python-скриптами: `backend\venv\Scripts\activate`

# Базовые команды

1. Проверка статуса Docker/Compose
   - `docker info`
   - `docker compose version`
2. Локальный прогон GitHub Actions (act)
   - `act workflow_dispatch --workflows .github/workflows/backend-ci.yml`
3. Управление секретами (пример через GitHub CLI)
   - `gh secret set SECRET_NAME --body "value"`

# Пошаговый процесс

1. **Планирование изменений**
   - Собрать требования (issue, story, gate)
   - Подтвердить окно внедрения с командой

2. **Анализ текущего состояния**
   - Проверить актуальность документации: `docs/ci-cd/README.md`
   - Снять состояние инфраструктуры (docker-compose, Terraform, Ansible)

3. **Подготовка окружения**
   - Обновить зависимости: `python -m pip install -r backend/requirements.txt`
   - Прогнать тесты: `cd backend; if ($?) { pytest }`
   - Проверить lint: `cd backend; if ($?) { flake8 }`

4. **Работа с CI/CD**
   - Проверить workflows `.github/workflows/*.yml`
   - При изменениях запустить dry-run через `act`
   - Зафиксировать обновления в `docs/ci-cd`

5. **Инфраструктурные изменения**
   - Обновить конфигурации Docker/K8s/Compose
   - Применить Terraform/Ansible (если используется)
   - Зафиксировать новые переменные окружения (Secrets/ConfigMaps)

6. **Валидация**
   - Запустить smoke-тесты
   - Проверить метрики Prometheus/Grafana
   - Убедиться в отсутствии регрессий (логирование, алерты)

7. **Деплой**
   - Staging: `./scripts/deploy-staging.ps1` (пример)
   - Production: запуск через GitHub Actions с ручным подтверждением
   - Отслеживать хелсчеки и журналы

8. **Мониторинг и откат**
   - Включить алерты (Slack, Email)
   - Подготовить стратегию rollback (docker image tag, миграции)
   - Документировать инциденты при необходимости

9. **Документация**
   - Обновить `docs/ci-cd/` и `docs/architecture/`
   - Зафиксировать изменения в story/epic (Dev Agent Record, Change Log)

# Чек-лист завершения

- [ ] Тесты (unit/integration) пройдены
- [ ] CI/CD workflows проверены/обновлены
- [ ] Секреты и переменные окружения синхронизированы
- [ ] Мониторинг и алерты активны
- [ ] Документация обновлена
- [ ] Сообщение команде отправлено (канал DevOps)

# Дополнительные материалы

- `docs/ci-cd/README.md`
- `.github/workflows/backend-ci.yml`
- `.github/workflows/frontend-ci.yml`
- `.github/workflows/pre-merge-checks.yml`
- `docs/architecture/14-cicd-deployment.md`
