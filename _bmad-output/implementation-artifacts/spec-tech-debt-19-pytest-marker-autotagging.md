---
title: 'Автоматическая разметка pytest-маркеров по каталогу (тех.долг п. 19)'
type: 'chore'
created: '2026-08-03'
status: 'in-review'
baseline_commit: '0e005137'
review_loop_iteration: 0
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

**Acceptance Criteria:**
- Given рабочее дерево после правки, when выполнен `pytest --collect-only -q -m "unit or integration or performance"`, then собрано 2699 тестов — столько же, сколько даёт полный `pytest --collect-only -q`.
- Given файл с явным `mark.integration` внутри `apps/`, when выполнен `pytest --collect-only -q -m unit`, then он в выборку не попадает.
- Given полный прогон `pytest -q -p no:randomly`, when он завершается, then число прошедших и упавших совпадает с прогоном до правки — хук меняет маркировку, не поведение.
- Given `pytest tests/unit -q` изолированно, when корневой conftest уже загружен, then Django-настройки по-прежнему конфигурируются из `tests/unit/conftest.py` без ошибок.

## Spec Change Log

## Design Notes

Первое совпадение выигрывает; пути сравниваются по `parts`, а не по строкам с разделителями, иначе `make test-local` на Windows разойдётся с Docker:

```python
_RULES = (
    (("tests", "performance"), "performance"),
    (("tests", "integration"), "integration"),
    (("tests", "functional"), "integration"),
    (("tests", "regression"), "integration"),
    (("tests", "unit"), "unit"),
    (("apps", "*", "tests", "integration"), "integration"),  # раньше общего apps/
    (("apps",), "unit"),
)
```

Отклонение от рекомендации (3) в tech-debt: вместо отдельного CI-шага с двумя `--collect-only` инвариант закреплён самим хуком. Полный сбор занимает ~7,5 мин — два сбора в каждом PR стоят 15 минут CI ради проверки, которую хук даёт бесплатно и притом локально.

## Verification

**Commands:** (из каталога `docker/`, префикс `docker compose -p freesport-test --env-file ../.env -f docker-compose.test.yml run --rm -T backend`)
- `pytest --collect-only -q -m "unit or integration or performance"` -- expected: `2699 tests collected`
- `pytest --collect-only -q` -- expected: то же число, без ошибок сбора
- `pytest tests/unit/test_pytest_marker_autotagging.py -q` -- expected: зелено
- `pytest -q -p no:randomly` -- expected: полный прогон, результат не хуже прогона до правки (≈33 мин)
- `cd backend && black --check conftest.py && flake8 conftest.py --max-line-length=120 --extend-ignore=E203,W503` -- expected: без замечаний

**Manual checks:**
- `docker-compose.test.yml` монтирует `../backend:/app` — новый `conftest.py` подхватывается без пересборки образа.
