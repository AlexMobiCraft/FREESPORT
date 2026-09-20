# CI/CD и релизы

Проект ведёт один разработчик. Проверки исполняются **один раз** — на PR в `develop`.
`main` — зеркало проверенного `develop`, релиз = fast-forward push в `main`.

- Процесс слияния и релиза: [merge-process.md](merge-process.md)
- Git-поток с командами (источник правды): [`.windsurf/rules/git-sync-workflow.md`](../../.windsurf/rules/git-sync-workflow.md)
- Деплой и окружения: [deploy-guide.md](deploy-guide.md)
- Тестирование в CI: [testing-guide.md](testing-guide.md)
- Лог релизных тегов: [change-log.md](change-log.md)

## Workflow-файлы

| Файл | Назначение | Триггер |
| --- | --- | --- |
| [`backend-ci.yml`](../../.github/workflows/backend-ci.yml) | Линтеры, типы, security, OpenAPI бэкенда (required) | PR в `develop` |
| [`frontend-ci.yml`](../../.github/workflows/frontend-ci.yml) | Тесты и сборка фронтенда (required) | PR в `develop` |
| [`main.yml`](../../.github/workflows/main.yml) | Django CI: полный прогон + покрытие (required) | PR в `develop`; тесты — кроме PR только из документации |
| [`api-contract.yml`](../../.github/workflows/api-contract.yml) | Синхронность OpenAPI и типов (required) | PR в `develop` |
| [`pre-merge-checks.yml`](../../.github/workflows/pre-merge-checks.yml) | Проверки качества кода (required) | PR в `develop` |
| [`e2e-tests.yml`](../../.github/workflows/e2e-tests.yml) | Playwright E2E (required) | PR в `develop`; тесты — только при правках во `frontend/**` |
| [`claude-code-review.yml`](../../.github/workflows/claude-code-review.yml) | Автоматическое ревью | PR в `develop` |
| [`deploy.yml`](../../.github/workflows/deploy.yml) | **Единственная прод-цепочка**: сборка образов → approval → SSH-деплой → откат | push в `main`, ручной запуск |
| [`sync-to-public.yml`](../../.github/workflows/sync-to-public.yml) | Синк чистой версии в публичный репозиторий | push в `main` |
| [`performance-tests.yml`](../../.github/workflows/performance-tests.yml) | Перф-тесты | cron 02:00 UTC, ручной запуск |
| [`setup-branch-protection.yml`](../../.github/workflows/setup-branch-protection.yml) | Защита веток | ручной запуск (`mode=check`/`apply`) |
| [`claude.yml`](../../.github/workflows/claude.yml) | Ответы Claude по упоминанию | комментарии в issue/PR |

Ни один workflow не запускается на push в `develop` и на push в `main`, кроме
`deploy.yml` и `sync-to-public.yml`. Это сделано намеренно (2026-09-20): синк в `main`
переносит тот самый коммит, который уже зелёный на PR, и push-прогоны перепроверяли
идентичный SHA во второй и третий раз.

## PR только из документации

`build (3.12)` (`main.yml`) держит ожидание всего гейта — ~13 минут. PR, который не
трогает ничего исполняемого, его пропускает: шаг «Нужен ли прогон» смотрит состав PR
через `gh pr diff` и скипает тяжёлые шаги. Такой PR проходит гейт примерно за минуту.

Решение принимается по **allowlist**, а не по имени ветки: `docs/*` — это обещание, а
не факт, и в такой ветке легко окажется правка кода. Прогон пропускается только если
**все** файлы PR попадают в список `docs/`, `_bmad-output/`, `.windsurf/`, `.claude/`,
любые `*.md`, `LICENSE`; любой незнакомый путь ведёт к полному прогону. Исключение
(`DENYLIST`) — `docs/api/*.yaml|json`: это контракт API, на него смотрят тесты схемы.

`.github/**` в allowlist не входит намеренно — правка CI обязана проверяться полностью.
Остальные пять чеков идут всегда: вместе они дают ~7 минут раннера и на ожидание почти
не влияют, так как исполняются параллельно.

Границы фильтра закреплены тестами `TestCIFilters::test_docs_only_filter_*`
(`backend/tests/unit/test_pytest_marker_autotagging.py`) — перебор конкретных путей в
обе стороны. Расширять allowlist без прогона этих тестов нельзя: `docs/` уже однажды
накрыл `docs/api/openapi.yaml`.

## Запуск релиза и откатa

```bash
# Релиз
git fetch origin
git push origin origin/develop:refs/heads/main

# Откат прода на прошлый релиз (без пересборки и тестов)
gh workflow run deploy.yml -f image_tag=<sha прошлого релиза>

# Ручной деплой текущего main
gh workflow run deploy.yml --ref main
```

Каждый релиз пушит образы в ghcr с тегами `:production` и `:<sha>`, поэтому любой
прошлый релиз доступен для откатa по своему SHA. Перед обновлением образов деплой
пишет digest'ы работающих контейнеров в `.last-release-digests` в каталоге деплоя.

## Защита веток

| Правило | `develop` | `main` |
| --- | --- | --- |
| Обязателен PR | да (0 аппрувов — один мейнтейнер) | нет |
| Required-чеки | 6 | нет |
| Force-push, удаление ветки | запрещены | запрещены |
| `enforce_admins` | да | да |

Применяется скриптом [`setup-branch-protection.sh`](../../.github/scripts/setup-branch-protection.sh)
через workflow `setup-branch-protection.yml` (нужен PAT с правами администратора в
секрете `BRANCH_PROTECTION_TOKEN`). `mode=check` только показывает состояние.

## Частые проблемы

- **Required-чек висит «Expected — waiting for status»** — у его workflow появился
  фильтр `paths` на `pull_request`. Required-контекст с таким фильтром не сообщает
  статус на PR, который эти пути не трогает, и блокирует мерж бессрочно.
- **Синк отклонён как non-fast-forward** — в `main` попал коммит вне `develop`.
- **Деплой упал** — job `rollback` в прогоне печатает готовые команды откатa.
- **Прогон деплоя висит в ожидании** — environment `production` требует одобрения
  (правило `required_reviewers`); одобрить нужно и на сборке, и на деплое, потому что
  прод-секрет `NEXT_PUBLIC_API_URL` доступен только внутри этого окружения.
