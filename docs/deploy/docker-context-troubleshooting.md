# Устранение неполадок с Docker контекстом

## Обзор

Docker контексты позволяют управлять несколькими Docker хостами (локальными и удаленными) из одного клиента Docker. В проекте FREESPORT используется контекст `freesport-remote` для работы с Docker на удаленном сервере `5.35.124.149`.

## Проблема

При выполнении скриптов обновления кода на сервере может возникнуть ошибка:
```
Failed to initialize: unable to resolve docker endpoint: context "freesport-remote": context not found
```

Это означает, что Docker контекст `freesport-remote` не существует или поврежден.

## Решение

### Автоматическое решение (рекомендуется)

Скрипты `update_server_code.ps1` и `run-tests-docker.ps1` теперь автоматически проверяют и создают Docker контекст при необходимости. Просто запустите скрипт как обычно:

```powershell
pwsh .\scripts\server\update_server_code.ps1
```

### Ручное создание контекста

Если автоматическое создание не работает, можно создать контекст вручную:

1. **Проверьте текущие контексты:**
   ```powershell
   docker context ls
   ```

2. **Создайте новый контекст:**
   ```powershell
   docker context create freesport-remote --docker "host=ssh://root@5.35.124.149"
   ```

3. **Проверьте подключение:**
   ```powershell
   docker --context freesport-remote ps
   ```

### Удаление и пересоздание контекста

Если контекст существует, но не работает правильно:

1. **Удалите поврежденный контекст:**
   ```powershell
   docker context rm freesport-remote
   ```

2. **Создайте его заново:**
   ```powershell
   docker context create freesport-remote --docker "host=ssh://root@5.35.124.149"
   ```

3. **Проверьте работу:**
   ```powershell
   docker --context freesport-remote ps
   ```

## Требования

Для работы Docker контекста с удаленным сервером необходимы:

1. **SSH доступ к серверу** с ключевой аутентификацией
2. **Docker установлен на сервере**
3. **Права пользователя** для управления Docker на сервере

### Проверка SSH подключения

```powershell
ssh root@5.35.124.149
```

### Проверка Docker на сервере

```powershell
ssh root@5.35.124.149 "docker ps"
```

## Частые проблемы

### 1. SSH ключ не найден

Ошибка: `SSH key not found`

Решение: Убедитесь, что SSH ключ существует и добавлен в ssh-agent:
```powershell
ssh-add ~/.ssh/id_ed25519
```

### 2. Нет доступа к Docker на сервере

Ошибка: `permission denied while trying to connect to the Docker daemon socket`

Решение: Добавьте пользователя в группу docker на сервере:
```bash
sudo usermod -aG docker root
# или для другого пользователя
sudo usermod -aG docker username
```

### 3. Контекст существует, но не работает

Ошибка: `Cannot connect to the Docker daemon`

Решение: Проверьте статус Docker на сервере:
```bash
ssh root@5.35.124.149 "sudo systemctl status docker"
```

## Полный процесс восстановления

1. **Проверьте SSH подключение:**
   ```powershell
   ssh root@5.35.124.149 "echo 'SSH connection works'"
   ```

2. **Проверьте Docker на сервере:**
   ```powershell
   ssh root@5.35.124.149 "docker --version && docker ps"
   ```

3. **Удалите старый контекст (если существует):**
   ```powershell
   docker context rm freesport-remote -f
   ```

4. **Создайте новый контекст:**
   ```powershell
   docker context create freesport-remote --docker "host=ssh://root@5.35.124.149"
   ```

5. **Проверьте работу контекста:**
   ```powershell
   docker --context freesport-remote ps
   ```

6. **Запустите скрипт обновления:**
   ```powershell
   pwsh .\scripts\server\update_server_code.ps1
   ```

## Дополнительная информация

- [Docker Context Documentation](https://docs.docker.com/engine/context/working-with-contexts/)
- [Docker Remote API](https://docs.docker.com/engine/api/)

## Контакты

При возникновении проблем, не описанных в этом документе, обратитесь к DevOps инженеру проекта.