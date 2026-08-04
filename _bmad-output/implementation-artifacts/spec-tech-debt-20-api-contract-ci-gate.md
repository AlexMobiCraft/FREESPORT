---
title: 'CI-гейт синхронизации API-контракта (тех.долг п. 20, цель 1)'
type: 'chore'
created: '2026-08-03'
status: 'in-review'
baseline_commit: '65569e5c'
review_loop_iteration: 1
context:
  - '{project-root}/_bmad-output/planning-artifacts/tech-debt.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `docs/api/openapi.yaml` и `frontend/src/types/api.generated.ts` коммитятся, но ничем не сверяются: CI их не регенерирует, `tsc` сгенерированный файл не видит (0 импортов), и рассинхрон контракта обнаружим только чтением диффа глазами. Сам `openapi.yaml` уже отстал от кода — последнее обновление `73992820`, 2026-07-26.

**Approach:** Management-команда сравнивает **разобранный** YAML со схемой, которую drf-spectacular строит из текущего кода, и отдельный workflow гоняет её вместе со сверкой регенерации TS-типов. Плюс разовая регенерация обоих артефактов, чтобы гейт стартовал с зелёного.

## Boundaries & Constraints

**Always:**
- Сравнивать **разобранные структуры**, а не текст: drf-spectacular недетерминирован в порядке HTTP-методов внутри пути, и побайтовое сравнение бессмысленно. Равенство словарей Python по построению нечувствительно к порядку ключей — это и закрывает недетерминизм.
- Списки, порядок которых семантически не значим (`tags`, `required`, `enum`, `parameters`), нормализуются перед сравнением.
- Отчёт о расхождении называет конкретные пути внутри документа (`components.schemas.ProductDetail.properties.opt4_price`), а не «файлы отличаются».
- `npm run generate:types` обязан воспроизводить закоммиченный файл побайтово. Сейчас **не воспроизводит**: коммит отформатирован Prettier, сырой вывод `openapi-typescript` — нет.

**Ask First:**
- Разовая регенерация удаляет или меняет endpoint, которого нет в коде → доложить, не «подгонять» результат.
- Нормализация понадобилась сверх четырёх перечисленных списков → доложить: это признак недетерминизма, который сделает гейт флаки.
- Сравнение полных документов даёт расхождения, не сводимые к дрейфу кода → доложить и сузить до `components.schemas` + множества пар «путь → метод», как предписывает tech-debt.

**Never:**
- Не типизировать DTO-слой фронта от генерации — отложено в `deferred-work.md` отдельной целью.
- Не удалять `api.generated.ts` и скрипт `generate:types` — вариант рассмотрен и отклонён автором долга.
- Не править сериализаторы, вью и `SPECTACULAR_SETTINGS` ради «красивой» схемы: гейт фиксирует контракт, а не переписывает его.
- Не понижать строгость гейта до `continue-on-error`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Синхронно | код и `openapi.yaml` совпадают | exit 0, сообщение об успехе | N/A |
| Поле добавлено в сериализатор | `opt4_price` есть в коде, нет в YAML | exit 1, назван путь `components.schemas.…` | перечень расхождений, до 20 записей |
| Порядок методов внутри пути | текст YAML иной, структура та же | exit 0 | N/A |
| Новый endpoint | путь есть в коде, нет в YAML | exit 1, назван путь и метод | N/A |
| Типы не пересобраны | `openapi.yaml` изменён, `api.generated.ts` — нет | шаг падает на непустом `git diff` | вывод diff в лог |
| Нет `docs/api/openapi.yaml` | файл отсутствует | exit 1 | внятное сообщение, не traceback |

</frozen-after-approval>

## Code Map

- `backend/apps/common/management/commands/check_api_docs.py` -- образец существующей команды-проверки; новая пишется по этому образцу.
- `backend/apps/common/management/commands/check_openapi_sync.py` -- **создаётся.** Генерирует схему в памяти, нормализует, сравнивает с закоммиченным YAML.
- `backend/freesport/settings/base.py:375` -- `SPECTACULAR_SETTINGS`; `TAGS`, `SERVERS`, `EXTENSIONS_INFO` (`x-logo`) приходят отсюда, поэтому регенерация их воспроизводит и ручных правок в YAML сохранять не требуется.
- `.github/workflows/backend-ci.yml` -- шаг «Validate OpenAPI schema generation» генерирует схему в `/tmp/schema.yml` и выбрасывает результат; поглощается новым workflow.
- `.github/workflows/api-contract.yml` -- **создаётся.**
- `frontend/package.json:22` -- `generate:types`, без прохода Prettier.
- `docs/api/openapi.yaml` -- 4826 строк; `components` с 2179, `servers` с 4803, `tags` с 4808.
- `frontend/src/types/api.generated.ts` -- 4913 строк, отформатирован Prettier; `.prettierignore` его не исключает.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/package.json` -- в `generate:types` добавлен проход `prettier --write`; после этого генерация побайтово идемпотентна (одинаковый md5 при повторном запуске)
- [x] `backend/apps/common/management/commands/check_openapi_sync.py` -- создана команда: `normalize`, `collect_differences`, отчёт по путям, `--schema-file`, `--limit`, `CommandError` (exit 1) при расхождении
- [x] `backend/tests/unit/test_check_openapi_sync.py` -- 22 теста: нормализация, независимость от порядка HTTP-методов, именование путей, ранние отказы команды
- [x] `backend/freesport/settings/base.py` -- в `SPECTACULAR_SETTINGS["TAGS"]` добавлен тег `Bonuses` (решение Alex, 2026-08-04; см. Design Notes — отступление от «Never»)
- [x] `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` -- разовая регенерация; 50 семантических расхождений устранено, состав endpoint'ов не изменился
- [x] `.github/workflows/api-contract.yml` -- создан: `pull_request` + `push` в `main`/`develop`, paths `backend/**`, `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts`, `frontend/package.json`
- [x] ~~`.github/workflows/backend-ci.yml` -- поглощённый шаг «Validate OpenAPI schema generation» убран~~ **Отменено по итогам ревью (итерация 1):** шаг возвращён, потому что живёт в джобе из required-контекстов, а новый workflow туда пока не входит
- [x] `_bmad-output/planning-artifacts/epics.md` -- NFR-3940-07 переписан: гейт появился; отдельно названо, чего он не проверяет
- [x] `_bmad-output/planning-artifacts/tech-debt.md` -- рекомендация (1) отмечена закрытой, цель (2) — отложенной

**Итерация 1 (по итогам ревью):**
- [x] `backend/apps/common/management/commands/check_openapi_sync.py` -- `_sort_key` (разнотипные скаляры и ключи), сверка типа при сравнении, `_short` (усечение отчёта), `load_schema` (`YAMLError`/`OSError` → `CommandError`), обёртка отказа генерации, guard на пустую схему, `options.get("limit")`, `--validate` в подсказке
- [x] `.github/workflows/api-contract.yml` -- `paths` дополнены (`package-lock.json`, `.prettierrc`, `.prettierignore`, `backend-ci.yml`); `git ls-files --error-unmatch` + `git status --porcelain` вместо `git diff --exit-code`; подсказка привязана к `id` шагов; добавлены служба redis, `concurrency`, `permissions`, `timeout-minutes`
- [x] `.github/scripts/setup-branch-protection.sh` -- контекст `Контракт синхронен с кодом` добавлен в оба блока; в шапку вписано предупреждение о трёх минах применения
- [x] `backend/tests/unit/test_check_openapi_sync.py` -- 45 тестов (было 22): смешанные типы, нестроковые ключи, `0`/`False`, усечение, битый и пустой YAML, нечитаемый файл, полный путь `handle()` с подменённой генерацией, лимит отчёта, отказ генерации
- [x] `_bmad-output/planning-artifacts/epics.md` -- NFR-3940-07 ослаблен до фактического: гейт краснеет, но не блокирует, пока защита веток не применена
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- отложены четыре находки: незастроенная защита веток и несовпадающие имена контекстов, неверная запись про защиту в `CLAUDE.md`, поиндексное сравнение `parameters`, размен на нормализации списков

**Acceptance Criteria:**
- ✅ Given дерево сразу после разовой регенерации, when выполнен `python manage.py check_openapi_sync`, then exit 0. **Проверено:** «Контракт синхронен с кодом».
- ✅ Given в сериализатор добавлено поле без регенерации YAML, when выполнена команда, then exit 1 и в выводе присутствует путь до этого поля. **Проверено на реальном дрейфе до регенерации:** 50 расхождений с точными путями, в том числе `components.schemas.RoleEnum.enum` (отсутствовал `wholesale_level4`) и `components.schemas.UserRegistrationRequest.properties.country`.
- ✅ Given `openapi.yaml` не менялся, when выполнен `npm run generate:types`, then `git diff frontend/src/types/api.generated.ts` пуст. **Проверено:** совпадающий md5 при повторном запуске.
- ✅ Given `openapi.yaml` перегенерирован, а `api.generated.ts` нет, when отработал `api-contract.yml`, then workflow падает на непустом `git diff`. **Проверено на закоммиченном дереве** (как в CI): `git diff --exit-code` даёт `0` при синхронном состоянии и `1` при внесённом расхождении. Сам workflow как целое исполнится впервые на PR — локально проверены его шаги, не оркестрация GitHub Actions.

## Spec Change Log

### 2026-08-04 — итерация 1, состязательное ревью (Blind Hunter + Edge Case Hunter)

**Что вскрылось (самое тяжёлое):** удаление шага «Validate OpenAPI schema generation» из `backend-ci.yml` меняло блокирующую проверку на необязательную — новый workflow не входил в required-контексты `setup-branch-protection.sh`. Спека предписала удаление, не рассмотрев слой принуждения вовсе.

**Проверка гипотезы изменила её вес.** `gh api` показал, что ни `main`, ни `develop` не защищены — «Branch not protected». Обязательных контекстов сегодня нет ни одного, так что регрессии блокировки фактически не было. Но строки в скрипте вдобавок не совпадают с реальными именами check-run (реальное — `build (3.12)`, в скрипте — «Django CI (build)»), и у трёх workflow есть фильтр `paths`, из-за которого required-контекст вешает PR бессрочно.

**Решения (Alex, 2026-08-04):**
1. Шаг в `backend-ci.yml` **возвращён** с комментарием, объясняющим, почему дублирование намеренно и когда его можно снять.
2. Контекст `Контракт синхронен с кодом` добавлен в оба блока `setup-branch-protection.sh`; в шапку скрипта вписано предупреждение о трёх минах применения.
3. Формулировка NFR-3940-07 ослаблена до фактической: гейт — сигнал, а не замок, пока защита не применена.

**Что ещё исправлено (патч-класс):** два подтверждённых `TypeError` — `normalize` на `enum` со смешанными типами и `None` (OpenAPI 3.1 это разрешает) и `collect_differences` на нестроковых ключах YAML (незакавыченный код ответа даёт `int`); пропуск расхождений `0`/`False` и `1`/`1.0` из-за питоновского равенства скаляров — добавлена сверка типа; необработанные `yaml.YAMLError`, `OSError` и отказ генерации схемы давали traceback вместо `CommandError`, вопреки строке I/O-матрицы; `options["limit"]` ронял `KeyError` при вызове `handle()` минуя argparse — именно так вызывают тесты; отчёт печатал `repr` целых поддеревьев без усечения; `git diff --exit-code` был слеп к удалённому из индекса `api.generated.ts` (регенерация создавала его заново как untracked, гейт зеленел) — добавлены `git ls-files --error-unmatch` и `git status --porcelain`; в `paths` не было `package-lock.json`, `.prettierrc`, `.prettierignore` и `backend-ci.yml`; `if: failure()` рапортовал «рассинхрон контракта» на обрыве `npm ci`; не было службы redis при заданном `REDIS_URL` и `django_redis` в кэше; добавлены `concurrency`, `permissions: contents: read`, `timeout-minutes`.

**KEEP (сохранить при любой переделке):** сравнение разобранных структур вместо текста — центральный аргумент подтверждён ревьюером независимо (`paths` и методы внутри пути суть YAML-отображения, `SORT_OPERATIONS: False` подтверждает источник недетерминизма); `_sort_key` с именем типа в ключе — без него первый же `enum` с `null` роняет команду; проход `prettier --write` внутри `generate:types`, иначе гейт падает на 100 % PR; разделение на два коммита — регенерация отдельно от кода гейта.

## Design Notes

Почему сравнение разобранных структур, а не текста: `yaml.safe_load` даёт словари, а равенство словарей в Python не зависит от порядка ключей. Именно в порядке ключей (HTTP-методы внутри пути) и сидит недетерминизм drf-spectacular, названный в tech-debt как ограничение. Значит полное сравнение документов **строже** предписанного там `components.schemas` + пары «путь → метод» и при этом не флаки — при условии нормализации списков, где порядок не значим:

```python
UNORDERED_LIST_KEYS = ("tags", "required", "enum")

def normalize(node):
    if isinstance(node, dict):
        return {k: (sorted(v) if k in UNORDERED_LIST_KEYS and _all_scalar(v) else normalize(v))
                for k, v in node.items()}
    if isinstance(node, list):
        return [normalize(x) for x in node]
    return node
```
`parameters` нормализуется отдельно — сортировкой по `(in, name)`, потому что это список словарей.

**Отступление от «Never», санкционированное человеком (Alex, 2026-08-04):** правка `SPECTACULAR_SETTINGS` запрещена спекой, но тег `Bonuses` с описанием существовал только в YAML — его дописали руками. Регенерация удалила бы описание группы в Swagger UI, то есть запрет привёл бы к регрессии, а не защитил от неё. Тег добавлен в настройки: источником истины стал код, что и есть цель гейта. Запрет остаётся в силе для всего остального — сериализаторы, вью и прочие настройки схемы не трогались.

Вопрос про службу postgres в `api-contract.yml` **закрыт консервативно, а не замером.** Гипотеза остаётся прежней: схема строится без обращения к БД, и существующий шаг `backend-ci.yml` выполнялся до миграций, то есть на пустой базе. Но проверить это можно только на самом runner'е — локальный прогон в Docker всегда идёт с поднятой БД и гипотезу не различает. Служба оставлена. Если понадобится экономить минуту прогона, её можно убрать и посмотреть на первый же PR; цена ошибки — красный CI, а не испорченные данные.

Мина, найденная при планировании: закоммиченный `api.generated.ts` прогнан через Prettier, а `openapi-typescript` выдаёт другое форматирование (двойные кавычки, иная разбивка строк). Проверка «регенерировать и сравнить» без шага Prettier дала бы дифф в 4867 добавленных и 4889 удалённых строк на неизменном контракте.

## Verification

**Commands:** (из каталога `docker/`, префикс `docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend`)

⚠️ В контейнер смонтирован **только `backend/`** — `docs/api/openapi.yaml` там недоступен, поэтому локально файл кладётся внутрь `backend/` и передаётся через `--schema-file`. На runner'е GitHub Actions репозиторий выложен целиком, и команда работает без аргументов. На Windows обязателен префикс `MSYS_NO_PATHCONV=1`, иначе Git Bash подменяет `/app/...` на путь вида `C:/Program Files/Git/app/...`.

- `cp docs/api/openapi.yaml backend/_committed_schema.yaml` затем `MSYS_NO_PATHCONV=1 docker compose … python manage.py check_openapi_sync --schema-file /app/_committed_schema.yaml` -- **проверено:** «Контракт синхронен с кодом»; временный файл удалить после проверки
- `pytest tests/unit/test_check_openapi_sync.py -q` -- **проверено:** 22 passed
- `cd frontend && npm run generate:types && git diff --exit-code src/types/api.generated.ts` -- **проверено:** exit 0 на закоммиченном дереве, exit 1 при внесённом расхождении
- `cd frontend && npx tsc --noEmit && npx prettier --check src/types/api.generated.ts` -- **проверено:** обе без ошибок
- `black --check` и `flake8 --max-line-length=120 --extend-ignore=E203,W503` на новых Python-файлах -- **проверено:** без замечаний

**Manual checks:**
- Дифф разовой регенерации просмотрен: 50 расхождений, все объясняются правками кода; состав endpoint'ов не изменился (проверено сравнением множеств путей), поэтому предохранитель «Ask First» не сработал.
- Полноценно workflow `api-contract.yml` исполнится впервые на PR — локально проверены его шаги, но не оркестрация GitHub Actions.
