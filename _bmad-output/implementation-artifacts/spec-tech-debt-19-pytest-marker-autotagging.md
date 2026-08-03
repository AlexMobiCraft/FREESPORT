---
title: 'Автоматическая разметка pytest-маркеров по каталогу (тех.долг п. 19)'
type: 'chore'
created: '2026-08-03'
status: 'done'
baseline_commit: '0e005137'
review_loop_iteration: 2
context:
  - '{project-root}/_bmad-output/planning-artifacts/tech-debt.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 852 из 2699 backend-тестов (31 %) не имеют ни `unit`, ни `integration` маркера, поэтому `make test-unit` + `make test-integration` молча пропускают треть пакета. Это уже дало ложно-зелёный результат на стори `security-wholesale-price-visibility` при пяти реально сломанных тестах. Правило записано в `project-context.md` §4, но ничем не обеспечено: каждый новый файл без маркера расширяет слепую зону.

**Approach:** Корневой `backend/conftest.py` с хуком `pytest_collection_modifyitems`, проставляющим маркер по каталогу теста; явный маркер в файле побеждает автоматический. Путь вне таблицы соответствия обрывает сбор с внятной ошибкой — это и есть механическое закрепление инварианта. Плюс маркер `performance` для перф-тестов, выводимых из обычного гейта.

## Boundaries & Constraints

**Always:**
- Явный `@pytest.mark.*` / `pytestmark` (`unit` / `integration` / `performance`) в файле всегда побеждает автоматический — хук ничего не переписывает.
- Маркер определяется **только путём файла**; таблица упорядочена, специфичное правило раньше общего.
- `backend/conftest.py` не импортирует Django и не трогает `settings`: он грузится раньше `backend/tests/unit/conftest.py`, который сам вызывает `settings.configure()`. Только `pytest` и stdlib.
- Логика «путь → маркер» — чистая функция, покрытая unit-тестами.

**Ask First:**
- Сбор по `-m "unit or integration or performance"` не сошёлся с полным сбором → доложить, не «дотягивать» цифру исключениями.
- Исключение `performance` уронило `--cov-fail-under` (65 в `backend-ci.yml`, 60 в `deploy.yml`) → доложить, порог не понижать.

**Never:**
- Не проставлять маркеры руками в ~100 файлах — вариант отклонён решением от 2026-08-03.
- Не менять содержимое, не удалять и не переносить существующие тесты.
- Не трогать маркеры `data_dependent` и `slow` — они ортогональны.
- Не чинить сломанный `docker/.env` в make-таргетах — вне объёма.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Каталог без маркера | `tests/unit/test_models/test_product_models.py` | `unit` | N/A |
| Явный маркер в `apps/` | `apps/products/tests/test_brand_api.py` с `mark.integration` | Остаётся `integration`, `unit` не добавляется | N/A |
| Вложенный integration в apps | `apps/products/tests/integration/test_import_orchestration.py`, маркера нет | `integration` (правило раньше `apps/` → `unit`) | N/A |
| Функциональные | `tests/functional/test_*.py` | `integration` | N/A |
| Перф | `tests/performance/test_search_performance.py` (помечен `slow`) | Добавляется `performance`, `slow` сохраняется | N/A |
| Django-style | `apps/pages/tests.py` (собирается по `python_files = tests.py`) | `unit` | N/A |
| Неизвестный каталог | новый `backend/tests/smoke/test_x.py` | Сбор прерван | `pytest.UsageError` с перечнем файлов и указанием дописать правило в `backend/conftest.py` |

</frozen-after-approval>

## Code Map

- `backend/conftest.py` -- **создаётся.** Корневой conftest (rootdir = `backend/`); сейчас отсутствует, хука `pytest_collection_modifyitems` в проекте нет вовсе.
- `backend/pytest.ini` -- объявлены `unit`, `integration`, `data_dependent`, `slow`; нужен `performance`.
- `backend/tests/unit/conftest.py` -- вызывает `settings.configure()` на импорте; причина запрета Django-импортов в корневом conftest.
- `.github/workflows/backend-ci.yml:195`, `deploy.yml:113` -- фильтр `-m "not integration and not data_dependent"` (исключающий — потому немаркированные в CI выполнялись).
- `.github/workflows/main.yml:123` -- `pytest` без `-m` вовсе.
- `Makefile:84-96` -- таргеты `test-unit` / `test-integration`.

## Tasks & Acceptance

**Execution:**
- [x] `backend/pytest.ini` -- добавлен маркер `performance`
- [x] `backend/conftest.py` -- создан: `PATH_RULES`, чистая `marker_for_path`, хук `pytest_collection_modifyitems` с `UsageError` на непокрытом пути
- [x] `backend/tests/unit/test_pytest_marker_autotagging.py` -- 20 тестов: все правила таблицы, приоритет специфичного, wildcard, `None` на непокрытом пути, инварианты самой таблицы
- [x] `.github/workflows/backend-ci.yml` -- в фильтр добавлено `and not performance`
- [x] `.github/workflows/deploy.yml` -- то же
- [x] `.github/workflows/main.yml` -- добавлен `-m "not performance"` (фильтра не было вовсе)
- [x] `Makefile` -- таргет `test-performance` + `.PHONY` + строка в `help`
- [x] `project-context.md` -- §4 переписан на автоматическую разметку
- [x] `backend/docs/testing-standards.md` -- добавлен раздел «Маркеры pytest»
- [x] `_bmad-output/planning-artifacts/tech-debt.md` -- п. 19 отмечен закрытым по образцу п. 18

**Итерация 2 (по итогам ревью):**
- [x] `backend/conftest.py` -- правило переписано на поиск самого глубокого каталога-категории вместо префиксных шаблонов; закрывает `apps/*/tests/{performance,functional,regression}` и вложенность глубже одного сегмента; добавлен `@pytest.hookimpl(tryfirst=True)`
- [x] `pytest.ini` (корень репозитория) -- добавлен маркер `performance`; файл существует и действует при запуске не из `backend/`
- [x] `pytest.ini` (оба) -- добавлен `norecursedirs`: служебный каталог с тестовым файлом больше не валит весь прогон
- [x] `backend/tests/unit/test_pytest_marker_autotagging.py` -- 39 тестов: покрыт сам хук (явный маркер побеждает, out-of-tree, `UsageError`), добавлен обход реального дерева и сверка обоих `pytest.ini` через `configparser`
- [x] `.github/workflows/performance-tests.yml` -- создан nightly-workflow (`schedule` + `workflow_dispatch`) для `-m performance`
- [x] `docs/architecture/10-testing-strategy.md`, `docs/architecture/ai-implementation/README.md` -- сняты противоречия: `unit` больше не означает «без БД»
- [x] `backend/docs/testing-standards.md`, `project-context.md` -- правило приведено к новой форме, задокументирована асимметрия `apps/` и таблица «где что исполняется»
- [x] Замер покрытия на суженном наборе `backend-ci.yml` и доклад -- **порог берётся, но впритык:** 1769 passed, 4 skipped, 937 deselected за 8:18; 40401 оператор, 14216 непокрытых → **64,81 %**, отображается как `65%`. `--cov-fail-under=65` не срабатывает только из-за округления coverage.py до целых (`round(64.81, 0) = 65`, условие `65 < 65` ложно). Запас ≈ 0,2 п.п. — решение по порогу за человеком

**Acceptance Criteria:**
- ✅ Given рабочее дерево после правки, when выполнен `pytest --collect-only -q -m "unit or integration or performance"`, then собрано столько же тестов, сколько даёт полный `pytest --collect-only -q`. **Проверено:** оба сбора дают 2738 (2699 до правки + 39 тестов самого правила); `unit` 1789 + `integration` 922 + `performance` 27 = 2738 ровно, пересечений нет.
- ✅ Given файл с явным `mark.integration` внутри `apps/`, when выполнен `pytest --collect-only -q -m unit`, then он в выборку не попадает. **Проверено** арифметикой сбора и прямым тестом хука `test_explicit_marker_wins`.
- ✅ Given полный прогон `pytest -q -p no:randomly`, when он завершается, then число прошедших и упавших совпадает с прогоном до правки — хук меняет маркировку, не поведение.
- ✅ Given `pytest tests/unit -q` изолированно, when корневой conftest уже загружен, then Django-настройки по-прежнему конфигурируются из `tests/unit/conftest.py` без ошибок. **Проверено:** 1161 passed, 2 skipped, 0 failed.
- ✅ Given новый тестовый файл в каталоге без категории, when запускается pytest, then сбор падает с `UsageError`, называющим файл. **Проверено** вручную на временном `tests/smoke/` и тестами `test_unmapped_item_raises_usage_error` / `test_usage_error_lists_every_unmapped_file`.

## Spec Change Log

### 2026-08-03 — итерация 1, состязательное ревью (Blind Hunter + Edge Case Hunter)

**Что вскрылось:** правка **сужает** покрывающий прогон `backend-ci.yml`. Фильтр там исключающий (`-m "not integration and not data_dependent"`), поэтому немаркированные тесты его проходили и выполнялись. После авторазметки 166 из них получили `integration` (150 из `tests/integration/` + 11 из `tests/functional/` + 5 из `apps/products/tests/integration/`) и выпали, вместе с 27 перф-тестами. Изменение, задуманное как расширение гейта, для основного backend-workflow его сузило. Исходная спека этого не предусмотрела — исключающий характер фильтра был замечен на этапе исследования, но вывод из него не сделан.

**Решения (Alex, 2026-08-03):**
1. `backend-ci.yml` остаётся быстрым unit-гейтом — фильтр теперь работает так, как был задуман. Полный прогон на каждом PR в `main`/`develop` даёт `main.yml` (триггеры `push` + `pull_request`, весь набор без `performance`), поэтому проверка корректности не потеряна — затронута только метрика покрытия. Обязателен замер фактического покрытия на суженном наборе и доклад: порог `--cov-fail-under=65` может не взяться, решение по нему — за человеком.
2. Перф-тесты получают отдельный nightly-workflow (`schedule` + `workflow_dispatch`). До правки они шли в `main.yml`; «не место в обычном гейте» не означало «не исполнять нигде».
3. Правки вносятся поверх коммита `37819af2`, откат не делается: механизм рабочий и подтверждён полным прогоном (2715 passed, 4 skipped, 0 failed), находки касаются краёв и состава CI.

**Что ещё поправлено (патч-класс):** корневой `pytest.ini` репозитория (существует, `pythonpath = backend .`) не содержал маркера `performance`; `apps/*/tests/{performance,functional,regression}` схлопывались в `unit`; шаблон с `*` совпадал ровно с одним сегментом, из-за чего `apps/products/api/tests/integration/` уезжал в `unit`; хук не был помечен `tryfirst`; отсутствовал `norecursedirs` (venv с нестандартным именем валил весь прогон); сам хук не был покрыт тестами — инвариант «явный маркер побеждает» не проверялся ничем; не было проверки, что все реальные тестовые каталоги покрыты правилами.

**KEEP (сохранить при любой переделке):** якорь `BACKEND_ROOT = Path(__file__).parent` вместо `config.rootpath` — именно он спасает разметку при запуске с корня репозитория, где действует другой `pytest.ini`; запрет Django-импортов в корневом conftest; чистая функция соответствия, отделённая от хука; сторож `UsageError` вместо CI-шага с двойным сбором.

## Design Notes

Первое совпадение выигрывает; пути сравниваются по `parts`, а не по строкам с разделителями, иначе `make test-local` на Windows разойдётся с Docker:

```python
CATEGORY_DIRS = {  # ищется среди сегментов пути, побеждает самый глубокий
    "unit": "unit",
    "integration": "integration",
    "functional": "integration",
    "regression": "integration",
    "performance": "performance",
}
DEFAULT_PREFIX_RULES = ((("apps",), "unit"),)  # запасной вариант, если категории нет
```

Итерация 2 заменила упорядоченную таблицу префиксов на этот вид. Префиксы совпадали ровно с одним сегментом на месте `*`, поэтому `apps/products/api/tests/integration/` уезжал в `unit`, а `apps/*/tests/{performance,functional,regression}` не различались вовсе. Поиск каталога-категории на любой глубине закрывает всё это одним правилом. Пути сравниваются по `parts`, а не по строкам с разделителями, иначе `make test-local` на Windows разойдётся с Docker.

Отклонение от рекомендации (3) в tech-debt: вместо отдельного CI-шага с двумя `--collect-only` инвариант закреплён самим хуком. Замер 2026-08-03: один `--collect-only` — ≈2:50, то есть отдельный CI-шаг с двумя сборами стоил бы ≈6 минут в каждом PR ради проверки, которую хук даёт бесплатно и притом локально, в момент написания теста.

## Verification

**Commands:** (из каталога `docker/`, префикс `docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend`)
- `pytest --collect-only -q -m "unit or integration or performance"` -- expected: столько же тестов, сколько даёт полный `pytest --collect-only -q`. **Проверено независимо 2026-08-03:** 2738 против 2738 (2699 до правки + 39 тестов самого правила), сбор ≈2:50
- `pytest --collect-only -q` -- expected: без ошибок сбора
- `pytest tests/unit/test_pytest_marker_autotagging.py -q` -- expected: зелено; 2 теста корневого `pytest.ini` пропускаются в контейнере, где смонтирован только `backend/`
- `pytest -q -p no:randomly` -- expected: полный прогон, результат не хуже прогона до правки (≈43 мин)
- `cd backend && black --check conftest.py && flake8 conftest.py --max-line-length=120 --extend-ignore=E203,W503` -- expected: без замечаний

**Manual checks:**
- `docker-compose.test.yml` монтирует `../backend:/app` — новый `conftest.py` подхватывается без пересборки образа.
