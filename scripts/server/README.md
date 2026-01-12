# Скрипты для работы с сервером FREESPORT

Эта директория содержит скрипты для автоматизации различных операций на удаленном сервере проекта FREESPORT.

## Подготовка к работе

### Проблема: Постоянный запрос пароля SSH

Если скрипты постоянно запрашивают пароль от SSH ключа, это означает, что `ssh-agent` не используется должным образом.

**Решение в 1 шаг:**

Запустите скрипт `setup_ssh.ps1`. Он настроит все необходимое для текущей сессии PowerShell.

```powershell
# Этот скрипт нужно запускать один раз для каждой новой сессии терминала
pwsh .\scripts\server\setup_ssh.ps1
```

**Что делает `setup_ssh.ps1`:**
1.  Запускает службу `ssh-agent`.
2.  **Устанавливает переменную окружения `$env:SSH_AUTH_SOCK`**, что критически важно для дочерних процессов (`docker`, `ssh`, `scp`).
3.  Добавляет ваш SSH ключ в агент (попросит пароль один раз, если он есть).
4.  Проверяет подключение к серверу.

После выполнения этого скрипта все остальные (`update_server_code.ps1`, `fix_docker_context.ps1` и т.д.) должны работать без запроса пароля.

---


## Доступные скрипты

### 1. update_server_code.ps1

**Назначение:** Обновление кода проекта на сервере и перезапуск контейнеров

**Использование:**

```powershell
# Стандартный запуск (текущая ветка, production compose)
pwsh .\scripts\server\update_server_code.ps1

# Указание конкретной ветки
pwsh .\scripts\server\update_server_code.ps1 -Branch feature/new-feature

# Указание другого пользователя и IP
pwsh .\scripts\server\update_server_code.ps1 -User alex -IP 5.35.124.149

# Использование тестового compose файла
pwsh .\scripts\server\update_server_code.ps1 -UseTestCompose

# Указание другого compose файла
pwsh .\scripts\server\update_server_code.ps1 -ComposeFile "docker/docker-compose.prod.yml"
```

**Что делает:**
1. Обновляет код из Git репозитория на сервере
2. Копирует локальный .env файл на сервер
3. Перезапускает Docker контейнеры (по умолчанию использует docker-compose.yml)
4. Выполняет миграции базы данных

**Параметры:**
- `-UseTestCompose` - Использовать docker-compose.test.yml вместо основного
- `-ComposeFile` - Указать путь к конкретному compose файлу
- `-Branch` - Указать ветку Git для обновления
- `-User` - Пользователь SSH (по умолчанию: root)
- `-IP` - IP-адрес сервера (по умолчанию: 5.35.124.149)

**Важно:** Скрипт автоматически проверяет и создает Docker контекст `freesport-remote` при необходимости.

---

### 2. fix_docker_context.ps1
**Назначение:** Восстановление Docker контекста для работы с удаленным сервером

**Использование:**
```powershell
# Стандартный запуск
pwsh .\scripts\server\fix_docker_context.ps1

# С указанием другого пользователя
pwsh .\scripts\server\fix_docker_context.ps1 -User alex
```

**Что делает:**
1. Проверяет SSH подключение к серверу
2. Проверяет работу Docker на сервере
3. Удаляет поврежденный Docker контекст (если существует)
4. Создает новый Docker контекст `freesport-remote`
5. Проверяет работу контекста

**Когда использовать:**
- При ошибке `context "freesport-remote": context not found`
- При проблемах с подключением к Docker на сервере
- После переустановки Docker на сервере

---

### 3. run-tests-docker.ps1
**Назначение:** Запуск тестов через Docker на удаленном сервере

**Использование:**
```powershell
# Стандартный запуск
pwsh .\scripts\server\run-tests-docker.ps1
```

**Что делает:**
1. Проверяет и создает Docker контекст при необходимости
2. Запускает тестовые контейнеры
3. Выполняет тесты проекта
4. Очищает тестовые контейнеры после выполнения

---

### 4. import_catalog_on_server.ps1
**Назначение:** Импорт каталога товаров из 1С напрямую на сервере

**Подробности:** См. [README_IMPORT_ON_SERVER.md](README_IMPORT_ON_SERVER.md)

---

## Общие требования

### На локальной машине:
- PowerShell 5.1 или выше
- OpenSSH клиент
- SSH ключ для доступа к серверу

### На сервере:
- Docker и Docker Compose
- Python и Django проект
- PostgreSQL база данных
- SSH доступ с ключевой аутентификацией

## Устранение неполадок

### Проблема с SSH подключением

**Симптомы:**
- Многократный запрос пароля
- Ошибка "Error connecting to agent: No such file or directory"
- "Permission denied" при подключении

**Решение:**
Запустите скрипт `setup_ssh.ps1` в начале вашей сессии терминала.

```powershell
pwsh .\scripts\server\setup_ssh.ps1
```
Он настроит `ssh-agent` и добавит ваш ключ, попросив пароль только один раз (если он есть).

### Проблема с Docker контекстом
Если вы видите ошибку:
```
Failed to initialize: unable to resolve docker endpoint: context "freesport-remote": context not found
```

**Решение 1 (автоматическое):**
```powershell
pwsh .\scripts\server\fix_docker_context.ps1
```

**Решение 2 (ручное):**
```powershell
docker context rm freesport-remote -f
docker context create freesport-remote --docker "host=ssh://root@5.35.124.149"
```

Подробная информация в [docker-context-troubleshooting.md](../../docs/docker-context-troubleshooting.md)

### Проблемы с SSH
```powershell
# Проверка SSH подключения
ssh root@5.35.124.149

# Проверка SSH ключей
ssh-add -l

# Добавление ключа в агент
ssh-add ~/.ssh/id_ed25519
```

### Проблемы с Docker на сервере
```powershell
# Проверка статуса Docker
ssh root@5.35.124.149 "sudo systemctl status docker"

# Проверка прав пользователя
ssh root@5.35.124.149 "groups"
```

## Структура проекта

```
scripts/server/
├── README.md                    # Этот файл
├── README_IMPORT_ON_SERVER.md   # Документация по импорту каталога
├── update_server_code.ps1       # Обновление кода на сервере
├── fix_docker_context.ps1       # Восстановление Docker контекста
├── run-tests-docker.ps1         # Запуск тестов
├── setup_ssh.ps1               # Настройка SSH окружения
└── import_catalog_on_server.ps1 # Импорт каталога
```

## Безопасность

- Все скрипты используют SSH-ключевую аутентификацию
- Пароли не хранятся в скриптах
- Рекомендуется использовать отдельные SSH ключи для разных окружений
- Перед выполнением скриптов убедитесь, что локальные изменения закоммичены

## Поддержка

При возникновении проблем:
1. Проверьте раздел "Устранение неполадок"
2. Ознакомьтесь с документацией по конкретному скрипту
3. Обратитесь к DevOps инженеру проекта