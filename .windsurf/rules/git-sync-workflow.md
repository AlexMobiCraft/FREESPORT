---
description: Порядок сохранения изменений в GitHub, синка develop -> main и откатa (solo-dev)
---

# Git workflow: develop как единственный гейт, main как зеркало

Проект ведёт один разработчик. Проверки CI проходят **один раз** — на PR в `develop`.
В `main` изменения попадают прямым fast-forward пушем; этот push и есть релиз.

```
feature/* -> PR -> develop --(fast-forward push по команде)--> main
                     ^                                          |
              6 required-чеков                                  v
              (единственный гейт)                     deploy.yml: approval -> прод
```

## Защита веток (setup-branch-protection.sh)

- `develop`: обязателен PR (0 аппрувов) + 6 required-чеков — «Бэкенд: качество кода»,
  «Фронтенд: тесты», «build (3.12)», «Контракт синхронен с кодом»,
  «Проверки качества кода», «E2E Tests». Список контекстов задан в
  `.github/scripts/setup-branch-protection.sh`; переименование job'а = переименование
  контекста, поэтому менять их нужно вместе, пока нет открытых PR.
- `main`: прямой push разрешён, PR и required-чеки сняты. Запрещены force-push
  и удаление ветки (enforce_admins = true — правила действуют и на владельца).

## Сохранение изменений

```bash
git checkout develop && git fetch origin && git reset --hard origin/develop
git checkout -b <type>/<name>        # feature/*, fix/*, docs/*, hotfix/*
# ... правки, коммит ...
git push -u origin <type>/<name>
gh pr create --base develop ...
gh pr merge <N> --auto --merge        # сольётся сам, когда позеленеет последний чек
```

`--auto` — предпочтительный способ: гейт идёт ~13 минут (его держит `build (3.12)`),
и сидеть над ним незачем. Мёрдж всё равно возможен только при всех шести зелёных
чеках. Без `--auto` (`gh pr merge <N> --merge`) сливается сразу, если чеки уже прошли.

Squash/rebase-merge запрещены: они переписывают коммиты и разводят историю веток,
из-за чего fast-forward синк перестаёт работать. Обе опции отключены и в настройках
репозитория, так что кнопок в UI нет.

Head-ветка PR удаляется при мёрдже автоматически (`delete_branch_on_merge`), убирать
её руками не нужно. Локальную копию — `git branch -d <type>/<name>`.

## Синк develop -> main = релиз (только по команде владельца)

```bash
git fetch origin
git log --oneline origin/main..origin/develop   # что уедет в прод
git push origin origin/develop:refs/heads/main  # fast-forward
```

Пушится `origin/develop`, а не локальный `develop`: в прод должно уехать ровно то,
что прошло гейт на origin.

- Push всегда fast-forward: `main` не содержит коммитов вне `develop`, поэтому
  обратный sync `main -> develop` не нужен никогда.
- Этот же push запускает `deploy.yml` (сборка prod-образов в ghcr → approval на
  environment `production` → SSH-деплой → health check) и `sync-to-public.yml`.
  Тестов на push нет: тот же SHA уже зелёный на PR в `develop`.
- НЕ создавать PR `develop -> main`: merge-коммит на `main` сломает FF-схему
  и вернёт необходимость back-merge.

## Что запускается и когда

| Событие | Прогоны |
|---|---|
| PR в `develop` | 6 required-чеков + Claude-ревью. E2E гоняет тесты только при правках во `frontend/**`, но статус сообщает всегда |
| push в `develop` (после мёрджа) | ничего |
| push в `main` (синк) | `deploy.yml` + `sync-to-public.yml` |
| ночью | `performance-tests.yml` (cron 02:00 UTC) |

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

## Откат

### Откатить релиз на проде

Образы каждого релиза лежат в ghcr с тегами `:production` и `:<sha>`, поэтому откат
не требует пересборки и тестов:

```bash
gh workflow run deploy.yml -f image_tag=<sha прошлого удачного релиза>
```

Прогон пропустит сборку и поднимет указанные образы. Если деплой упал, его job
`rollback` печатает в summary готовые команды и SHA предыдущего коммита `main`.
На сервере точка возврата — файл `.last-release-digests` в каталоге деплоя
(digest'ы образов, работавших до обновления) и дампы БД в `backups/`.

### Откатить код в main

```bash
git fetch origin
git log --oneline origin/develop        # найти коммит, который был в main до релиза
gh pr create --base develop ...         # реверт делается через PR в develop
```

Правильный путь — отменить изменение в `develop` (revert-коммит через PR, гейт
отработает) и синкнуть `main` снова. Прямой откат `main` невозможен без force-push,
который запрещён намеренно.

### Откатить саму эту схему

Схема введена двумя PR: #223 (гейт на develop) и PR «единый прогон» (удаление дублей
сборок и деплоев). Возврат к прежнему поведению:

```bash
gh pr revert <N>   # или git revert <merge-sha> -m 1 в ветке под PR в develop

# вернуть required-чеки и обязательный PR на main:
#   в .github/scripts/setup-branch-protection.sh убрать ветку main из if в
#   protection_payload(), затем Actions -> Setup Branch Protection -> mode=apply

# вернуть squash/rebase-merge:
gh api -X PATCH repos/AlexMobiCraft/FREESPORT \
  -F allow_squash_merge=true -F allow_rebase_merge=true
```
