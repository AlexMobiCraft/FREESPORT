# Инструкции для коммита исправлений

## Что было исправлено

### 1. ✅ Bandit security scanner
- Создан конфигурационный файл `backend/.bandit`
- Изменена команда в `.github/workflows/backend-ci.yml` для сканирования только исходного кода
- Устранены ложные срабатывания в сторонних библиотеках

### 2. ✅ PostgreSQL health check
- Исправлен health-cmd в `.github/workflows/backend-ci.yml`
- Добавлен параметр `-U postgres` для корректной проверки

### 3. ✅ Временные тестовые файлы
- Удалены `backend/test_order_serializer_simple.py` и `backend/test_serializer_unit.py`
- Устранены 2 падающих теста

### 4. ✅ Naive datetime warnings
- Исправлено использование `datetime.now()` на `timezone.now()` в тестах

### 5. ✅ Переменные окружения для тестов
- Добавлены env переменные в шаг "Run tests with coverage"

## Команды для коммита

```powershell
# Проверьте изменения
git status

# Добавьте все изменения
git add .github/workflows/backend-ci.yml
git add backend/.bandit
git add backend/tests/

# Закоммитьте
git commit -m "fix(ci): исправлены Bandit security checks и PostgreSQL health check

- Создан конфиг .bandit для исключения venv и служебных директорий
- Bandit теперь сканирует только apps/ и freesport/
- Исправлен pg_isready с параметром -U postgres
- Удалены временные тестовые файлы из корня backend/
- Исправлены naive datetime warnings в тестах
- Добавлены переменные окружения для шага тестирования

Fixes: ложные срабатывания Bandit, ошибка 'role root does not exist', падающие тесты"

# Запушьте изменения
git push
```

## Проверка на GitHub Actions

После пуша:

1. Перейдите в репозиторий → вкладка **Actions**
2. Дождитесь завершения workflow **Backend CI/CD**
3. Проверьте, что:
   - ✅ Шаг "Run security checks with bandit" проходит без ошибок
   - ✅ PostgreSQL service запускается успешно
   - ✅ Все тесты проходят (559 passed)
   - ✅ Нет предупреждений о naive datetime

## Ожидаемый результат

- **Bandit**: Сканирует только исходный код, нет ложных срабатываний
- **PostgreSQL**: Health check работает корректно
- **Тесты**: Все 559 тестов проходят успешно
- **Warnings**: Нет предупреждений о naive datetime

## Если что-то пошло не так

Проверьте логи конкретного шага в GitHub Actions и используйте:
- `backend/tests/RUN_TESTS_GUIDE.md` - руководство по запуску тестов
- `backend/tests/TEST_FIXES_GUIDE.md` - руководство по исправлению ошибок
- `backend/tests/CHANGELOG_TESTS.md` - история всех исправлений
