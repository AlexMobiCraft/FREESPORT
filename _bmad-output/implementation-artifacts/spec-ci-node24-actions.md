---
title: 'CI: перевод всех GitHub Actions на Node 24'
type: 'chore'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
baseline_commit: '849dd3c071895696413fd1fb6d261e504a9b47c5'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** GitHub принудительно запускает node20-экшены на Node 24 и выдаёт deprecation-предупреждение (замечено в workflow «E2E Tests»). Затронуты все 13 файлов `.github/workflows/`, включая `deploy.yml`; после EOL Node 20 такие экшены перестанут работать.

**Approach:** Поднять каждый сторонний экшен до последнего мажора, который объявляет `runs.using: node24`, и одновременно исправить инпуты, сломанные при переходе через мажоры (в первую очередь `codecov-action`: `file` → `files`).

## Boundaries & Constraints

**Always:**
- Целевые версии — последний мажор каждого экшена (проверено через `gh api` 2026-09-07): `actions/checkout@v7`, `actions/setup-node@v7`, `actions/upload-artifact@v7`, `actions/setup-python@v7`, `actions/cache@v6`, `actions/github-script@v9`, `codecov/codecov-action@v7`, `docker/setup-buildx-action@v4`, `docker/login-action@v4`, `docker/metadata-action@v6`, `docker/build-push-action@v7`, `webfactory/ssh-agent@v0.10.0`.
- Стиль ссылок сохраняется как в репозитории: плавающий мажорный тег (`@v7`), без пиннинга по SHA. Исключение — `webfactory/ssh-agent`, где мажорного тега нет: точная версия `v0.10.0`.
- Работа ведётся в новой ветке `chore/ci-node24-actions` от `origin/develop`. Незакоммиченные правки `AGENTS.md`, `CLAUDE.md`, `sprint-status.yaml` и файл стори `41-7-*.md` в коммит не попадают.

**Ask First:**
- Любое изменение логики шага, кроме версии экшена и переименования инпута `file` → `files`.
- Любой откат на более старый мажор, если выяснится несовместимость.

**Never:**
- Не трогать `anthropics/claude-code-action@v1` — composite-экшен, node20-предупреждения не даёт.
- Не менять триггеры, матрицы, `runs-on`, версии Python/Node, набор шагов и условия `if:`.
- Не добавлять пиннинг по SHA и не вводить Dependabot/renovate в рамках этой правки.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Обычный прогон CI | push/PR в `develop` | Все workflow зелёные, в логах нет строки «Node.js 20 is deprecated» | N/A |
| Загрузка покрытия | `frontend-ci.yml` и `main.yml` вызывают codecov@v7 | Отчёт принят: путь передан через `files:`, `flags`/`name`/`token` сохранены | `fail_ci_if_error: false` — CI не падает при сбое загрузки |
| Скрипты github-script | `require('fs')` в `pre-merge-checks.yml` | Работает: v9 по-прежнему инжектит `require` (`wrap-require`) | Падение шага → чинить скрипт, не откатывать мажор |
| Сборка и push образов | jobs с `docker/build-push-action@v7` | Образы собраны и запушены в ghcr.io, теги от `metadata-action@v6` не изменились | `continue-on-error` там, где он уже стоит |
| Деплой на прод | `deploy.yml`, ssh-agent@v0.10.0 | SSH-ключ загружен, деплой-шаги отрабатывают как раньше | Ручной запуск workflow; при сбое — откат версии ssh-agent |

</frozen-after-approval>

## Code Map

Основные правки — в `.github/workflows/` (13 файлов). GitNexus-символов здесь нет, `impact` неприменим.
Дополнительно (по итогам ревью): `docs/testing-docker.md:425`, `scripts/docs/README.md:326,329` — CI-шаблоны для разработчиков с теми же версиями.

- `api-contract.yml` — checkout, setup-python, cache, setup-node
- `backend-ci.yml` — checkout×2, setup-python, cache, upload-artifact, docker×4, github-script×2
- `claude.yml`, `claude-code-review.yml` — только checkout
- `deploy.yml` — checkout×3, setup-python, cache, setup-node, docker×6, ssh-agent, github-script (**самый рискованный файл**)
- `e2e-tests.yml` — checkout, setup-node, upload-artifact×2 (исходная жалоба)
- `frontend-ci.yml` — checkout×2, setup-node, upload-artifact, codecov (**инпут `file`**), docker×4, github-script×2
- `main.yml` — checkout×2, setup-python, codecov (**инпут `file`**)
- `merge-branches.yml` — checkout×2
- `performance-tests.yml` — checkout, setup-python, cache, github-script
- `pre-merge-checks.yml` — checkout, upload-artifact, github-script
- `setup-branch-protection.yml` — checkout, github-script
- `sync-to-public.yml` — checkout

## Tasks & Acceptance

**Execution:**
- [x] Создать ветку `chore/ci-node24-actions` от `origin/develop` — изолировать правку от незакоммиченных docs на `main`.
- [x] `.github/workflows/*.yml` — поднять версии всех экшенов из списка «Always» во всех 13 файлах — устранить node20.
- [x] `.github/workflows/frontend-ci.yml` и `.github/workflows/main.yml` — переименовать инпут codecov `file:` → `files:` — в v5+ `file` удалён, иначе загрузка покрытия молча ломается.
- [x] Проверить синтаксис YAML и отсутствие остаточных node20-версий (команды ниже) — до коммита.
- [x] `npx gitnexus detect-changes --scope all` — подтвердить, что затронуты только workflow-файлы.
- [x] Удалить `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` из 7 workflow — обходной путь стал мёртвым конфигом, маскирующим откат экшена на node20 (по итогам ревью, согласовано с пользователем).
- [x] 4 шага `docker/build-push-action` — добавить `DOCKER_BUILD_SUMMARY: false` и `DOCKER_BUILD_RECORD_UPLOAD: false` — v6 включил build summary и выгрузку build record по умолчанию (по итогам ревью).
- [x] `.github/workflows/frontend-ci.yml` — `files: frontend/coverage/lcov.info` вместо несуществующего `coverage-final.json` — vitest пишет `lcov`, а не `json` (по итогам ревью).
- [x] `docs/testing-docker.md`, `scripts/docs/README.md` — обновить версии в CI-шаблонах (по итогам ревью).

**Acceptance Criteria:**
- Given ветка `chore/ci-node24-actions` запушена, when отрабатывают `frontend-ci`, `backend-ci`, `main`, `e2e-tests`, `api-contract`, `pre-merge-checks`, then все job'ы завершаются с тем же результатом, что до правки, и ни в одном логе нет «Node.js 20 is deprecated». Пять workflow (`deploy`, `merge-branches`, `performance-tests`, `setup-branch-protection`, `sync-to-public`) на фича-ветке не запускаются — проверяются отдельно.
- Given grep по **всем** экшенам, включая `docker/*`, `codecov/*` и `webfactory/ssh-agent`, when выполнен, then нет версий ниже целевых из списка «Always» (команда — в разделе Verification).
- Given `deploy.yml` не запускается автоматически, when правка смержена, then деплой-workflow проверяется отдельным ручным запуском перед следующим релизом (риск зафиксирован в PR-описании).

## Spec Change Log

- **2026-09-07, итерация ревью 1 (без loopback).** Находки Blind Hunter и Edge Case Hunter, подтверждённые по первоисточникам: (1) `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` остался в 7 workflow — обходной путь ровно под эту проблему, после апгрейда мёртвый; (2) `build-push-action` v5→v7 проходит через v6, где build summary и выгрузка build record включились по умолчанию, а в репозитории все свои артефакты живут `retention-days: 1`; (3) codecov на фронте указывал в несуществующий `coverage-final.json` (vitest пишет `lcov.info`) — предсуществующий баг ровно в правленой строке; (4) CI-шаблоны в двух живых доках остались на старых версиях. Все четыре правки согласованы с пользователем как «Ask First» и внесены в ту же ветку; спека дополнена задачами и расширенным grep-критерием. **Известно-плохое состояние, которого избегаем:** мёртвый флаг, маскирующий будущий откат на node20, и молча неработающая загрузка покрытия фронта под `fail_ci_if_error: false`. **KEEP:** проверка каждого мажора по `runs.using` в `action.yml` (обнаружила, что `upload-artifact@v5` и `build-push-action@v6` — всё ещё node20) и опровержение ложной находки про семантику `file:`→`files:` (в codecov v4 автопоиск отчётов тоже был включён по умолчанию).

## Design Notes

Ключевые ловушки версий (проверено по `action.yml` каждого тега):
- `actions/upload-artifact@v5` **всё ещё node20** — минимально пригоден только v6; берём v7.
- `docker/build-push-action@v6` **тоже node20** — минимум v7.
- `codecov/codecov-action` с v5 — composite-обёртка над Codecov CLI; инпут `file` удалён (в v7 в `action.yml` есть только `files`).
- `actions/github-script@v9`: `require('@actions/github')` больше не работает, а `getOctokit` стал инжектируемым параметром. В нашем коде ни того, ни другого нет — есть только `require('fs')` в `pre-merge-checks.yml`, который v9 поддерживает.
- `actions/setup-node@v5+` включает автокеширование при наличии `packageManager` в `package.json`; у нас `cache: "npm"` задан явно, конфликта нет.
- Все job'ы идут на `ubuntu-latest` — требование «runner ≥ 2.327.1» выполняется автоматически.

## Verification

**Commands:**
- `backend/venv/Scripts/python.exe -c "import yaml,glob;print(len([yaml.safe_load(open(f,encoding='utf-8')) for f in glob.glob('.github/workflows/*.yml')]),'ok')"` — expected: `13 ok`
- `grep -rnE "checkout@v[0-6]|setup-node@v[0-6]|upload-artifact@v[0-6]|setup-python@v[0-6]|cache@v[0-5]|github-script@v[0-8]|codecov-action@v[0-6]|setup-buildx-action@v[0-3]|login-action@v[0-3]|metadata-action@v[0-5]|build-push-action@v[0-6]|ssh-agent@v0\.9" .github/workflows/` — expected: пусто (покрывает все 12 экшенов, а не только `actions/*`)
- `grep -rn "FORCE_JAVASCRIPT" .github/workflows/` — expected: пусто
- `grep -rn "file:" .github/workflows/frontend-ci.yml .github/workflows/main.yml` — expected: только `files:` рядом с codecov (совпадения `file: backend/Dockerfile` в docker-шагах — легитимны)
- `git diff --stat` — expected: `.github/workflows/` (13 файлов), `docs/testing-docker.md`, `scripts/docs/README.md`

**Manual checks (if no CLI):**
- После push ветки открыть Actions и убедиться, что в логах `e2e-tests` и `frontend-ci` предупреждение о Node 20 исчезло, а шаг codecov отработал.

## Suggested Review Order

**Исходная жалоба**

- Тот самый workflow из сообщения об ошибке: три экшена подняты, `env:` с мёртвым флагом удалён целиком.
  [`e2e-tests.yml:35`](../../.github/workflows/e2e-tests.yml#L35)

**Поведенческие правки (не только номер версии)**

- Путь покрытия фронта: `lcov.info` вместо несуществующего `coverage-final.json`, который vitest никогда не писал.
  [`frontend-ci.yml:103`](../../.github/workflows/frontend-ci.yml#L103)

- Инпут codecov `file` удалён в v5+; бэкенд-отчёт переведён на `files`.
  [`main.yml:176`](../../.github/workflows/main.yml#L176)

- v6 включил build summary и выгрузку build record — гасим оба env, чтобы не копить `.dockerbuild`.
  [`backend-ci.yml:268`](../../.github/workflows/backend-ci.yml#L268)

**Максимальный риск: прод-путь**

- Ключ прода: 0.x-экшен без контракта стабильности, единственный автоматически не проверяемый шаг.
  [`deploy.yml:236`](../../.github/workflows/deploy.yml#L236)

- Две сборки образов на новом мажоре; `deploy.yml` запускается только вручную.
  [`deploy.yml:186`](../../.github/workflows/deploy.yml#L186)

**Приватные данные и скрипты**

- Вложенный checkout приватного data-репо с `token:` — от него зависят ~32 теста 1С и порог покрытия.
  [`main.yml:63`](../../.github/workflows/main.yml#L63)

- Единственный `require()` в репозитории; v9 его по-прежнему инжектит через `wrapRequire`.
  [`pre-merge-checks.yml:293`](../../.github/workflows/pre-merge-checks.yml#L293)

**Периферия**

- Мерж этой ветки триггерит workflow: его собственный файл в `paths` (подробности — в `deferred-work.md`).
  [`setup-branch-protection.yml:27`](../../.github/workflows/setup-branch-protection.yml#L27)

- CI-шаблоны для разработчиков — чтобы доки не учили версиям, от которых уходим.
  [`testing-docker.md:425`](../../docs/testing-docker.md#L425)

- Тот же шаблон в руководстве по скриптам документации.
  [`README.md:326`](../../scripts/docs/README.md#L326)
