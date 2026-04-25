# 🚀 CI/CD и автоматизация слияния

## 📋 Обзор

В этом разделе описана система непрерывной интеграции и доставки (CI/CD) проекта, включая автоматизированный процесс слияния веток `develop` и `main`.

## 🏗️ Архитектура CI/CD

### Основные компоненты

- **[Автоматическое слияние веток](merge-process.md)** - основной процесс слияния
- **[Быстрый старт](merge-quickstart.md)** - краткая инструкция по использованию
- **[Правила защиты веток](../.github/workflows/setup-branch-protection.yml)** - настройка безопасности
- **[Проверки перед слиянием](../.github/workflows/pre-merge-checks.yml)** - контроль качества

### Workflow файлы

| Файл                                                                              | Назначение                   | Триггер                            |
| --------------------------------------------------------------------------------- | ---------------------------- | ---------------------------------- |
| [`deploy.yml`](../.github/workflows/deploy.yml)                                   | **Деплой на сервер**         | Ручной запуск (workflow_dispatch)  |
| [`merge-branches.yml`](../.github/workflows/merge-branches.yml)                   | Автоматическое слияние веток | Расписание/ручной запуск           |
| [`setup-branch-protection.yml`](../.github/workflows/setup-branch-protection.yml) | Настройка правил защиты      | Создание репозитория/ручной запуск |
| [`pre-merge-checks.yml`](../.github/workflows/pre-merge-checks.yml)               | Проверки перед слиянием      | Pull Request                       |
| [`backend-ci.yml`](../.github/workflows/backend-ci.yml)                           | CI/CD для бэкенда            | Push/PR в main/develop             |
| [`frontend-ci.yml`](../.github/workflows/frontend-ci.yml)                         | CI/CD для фронтенда          | Push/PR в main/develop             |

## Процесс слияния

### Стратегия

Мы используем **Squash Merge** для поддержания чистой истории коммитов в основной ветке.

### Автоматизация

- **По расписанию**: ежедневно в 9:00 UTC
- **Вручную**: через GitHub Actions UI или CLI
- **Проверки**: автоматические тесты и валидация

### Безопасность

- **Защита веток**: branch protection rules
- **Обязательные проверки**: CI/CD, тесты, безопасность
- **Одобрения**: минимум 1 ревью для слияния

## Быстрый старт

### Запуск деплоя

```bash
# Деплой на production
gh workflow run deploy.yml

# Пропустить тесты (только для hotfix)
gh workflow run deploy.yml -f skip_tests=true

# Или через UI: Actions → "Deploy to Server" → "Run workflow"
```

### Запуск слияния

```bash
# Через GitHub CLI
gh workflow run "Автоматическое слияние веток"

# Или через UI: Actions → "Автоматическое слияние веток" → "Run workflow"
```

### Мониторинг

- **Статус**: GitHub Actions → "Автоматическое слияние веток"
- **Логи**: детальные логи каждого шага
- **Уведомления**: автоматические уведомления о результате

## 📊 Метрики и мониторинг

### Ключевые показатели

- ✅ **Успешность слияний**: отслеживание успешных/неудачных слияний
- ⏱️ **Время выполнения**: среднее время процесса слияния
- 🔍 **Качество кода**: результаты проверок перед слиянием
- 🚨 **Проблемы**: конфликты, проваленные проверки

### Отчеты

- **Артефакты**: отчеты о проверках в GitHub Actions
- **Комментарии**: автоматические комментарии в Pull Request
- **Issues**: создание issues для отслеживания проблем

## 🔧 Устранение неполадок

### Частые проблемы

1. **Конфликты слияния**
   - Причина: несовместимые изменения
   - Решение: разрешите конфликты локально

2. **Проваленные проверки**
   - Причина: ошибки в тестах или сборке
   - Решение: исправьте ошибки в исходной ветке

3. **Отсутствие одобрений**
   - Причина: требуется ревью для слияния
   - Решение: запросите ревью у коллеги

### Поддержка

- **Документация**: [Полный процесс слияния](merge-process.md)
- **Issues**: создайте issue с меткой `merge-help`
- **DevOps**: обратитесь к команде DevOps

## 📚 Дополнительные ресурсы

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [Squash Merge Best Practices](https://www.atlassian.com/git/tutorials/merging-vs-rebasing)

---

_Последнее обновление: $(date +%Y-%m-%d)_
_Версия документации: 1.0_
