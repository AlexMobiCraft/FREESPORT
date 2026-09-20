# Слияние и релиз: develop как гейт, main как зеркало

> Пересмотрено 2026-09-20. До этого здесь описывался workflow `merge-branches.yml`
> (ежедневное автослияние `develop -> main` по cron в 9:00 UTC со стратегией squash).
> Он удалён: автомёрдж срабатывал без команды владельца, squash переписывал коммиты и
> разводил историю веток, а merge-коммит на `main` требовал обратного PR в `develop`.

## Схема

```
feature/* -> PR -> develop --(fast-forward push по команде)--> main
                     ^                                          |
              6 required-чеков                                  v
              (единственный гейт)                      deploy.yml: approval -> прод
```

- `develop` — единственное место, где исполняются проверки. Обязателен PR, 6 required-чеков:
  «Бэкенд: качество кода», «Фронтенд: тесты», «build (3.12)», «Контракт синхронен с кодом»,
  «Проверки качества кода», «E2E Tests». pytest исполняется один раз — в «build (3.12)»
  (`main.yml`), там же считается покрытие. E2E прогоняет тесты только при правках во
  `frontend/**`, но статус контекста сообщает на каждом PR — иначе мерж вис бы бессрочно.
- `main` — зеркало проверенного `develop`. Прямой push, PR и required-чеки сняты,
  force-push и удаление запрещены (`enforce_admins = true`).
- Проверки на PR в `main` и обратный merge `main -> develop` больше не существуют как
  операции: `main` не содержит коммитов вне `develop`.

## Стратегия слияния

Только **merge commit** (`gh pr merge N --auto --merge`). Squash и rebase запрещены: они
переписывают коммиты, из-за чего `main` и `develop` расходятся и fast-forward синк
перестаёт работать. Обе опции отключены и на уровне репозитория
(`allow_squash_merge = false`, `allow_rebase_merge = false`).

## Порядок работы

Полная процедура с командами — [`.windsurf/rules/git-sync-workflow.md`](../../.windsurf/rules/git-sync-workflow.md)
(единственный источник правды по git-потоку). Коротко:

```bash
# 1. Работа
git checkout develop && git fetch origin && git reset --hard origin/develop
git checkout -b feature/<name>
git push -u origin feature/<name>
gh pr create --base develop ...
gh pr merge <N> --auto --merge   # сольётся сам, когда позеленеет последний чек

# 2. Релиз (только по команде владельца)
git fetch origin
git log --oneline origin/main..origin/develop    # что уедет в прод
git push origin origin/develop:refs/heads/main   # fast-forward = релиз
```

Push в `main` запускает `deploy.yml` (сборка образов → approval на environment
`production` → SSH-деплой → health check) и `sync-to-public.yml`. Больше на push в
`main` не запускается ничего: тесты уже прошли на PR в `develop` по тому же коммиту.

## Когда что исполняется

| Событие | Что запускается |
|---|---|
| PR в `develop` | 6 required-чеков + Claude-ревью |
| push в `develop` | ничего |
| push в `main` | `deploy.yml` (с approval) + `sync-to-public.yml` |
| ночью по cron | `performance-tests.yml` |

## Если что-то пошло не так

- **Синк отклонён как non-fast-forward** — в `main` попал коммит вне `develop`.
  Разобраться до продолжения, см. раздел «Откат» в `git-sync-workflow.md`.
- **Деплой упал** — job `rollback` в прогоне печатает готовые команды откатa
  (тег прошлого релиза для входа `image_tag`, digest'ы из `.last-release-digests`).
- **Required-чек висит «Expected — waiting for status»** — у его workflow появился
  фильтр `paths` на `pull_request`. Такой фильтр несовместим с required-контекстом.
