---
title: 'Хвосты тех.долга 19: перф/медленные тесты вне PR-гейта, out-of-tree тесты, рабочие make-таргеты'
type: 'chore'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 1
baseline_commit: '22b99629'
context:
  - '{project-root}/backend/docs/testing-standards.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-tech-debt-19-pytest-marker-autotagging.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Четыре пункта, отложенные ревью tech-debt-19, оставили механизм разметки доведённым наполовину: (1) стресс-тесты `test_pages_performance.py` помечены явным `integration` и потому гоняются на каждом PR, хотя «перф-тест» задан местоположением файла, а не свойством теста; (2) маркер `slow` объявлен в обоих `pytest.ini`, но не подключён ни к одному гейту — таймингозависимый флак `test_retrieve_product_with_100_variants_under_500ms` остаётся в быстром гейте и уже валил прогон; (3) тест, чей путь уходит за пределы `backend/`, хук пропускает молча — ровно тот класс тихого выпадения, ради которого хук написан; (4) все таргеты `make test-*`, включая заявленный документацией `test-performance`, падают с `couldn't find env file`, потому что ищут несуществующий `docker/.env`.

**Approach:** Доводим до конца уже существующие механизмы, новых не вводим: явный `performance` на стресс-тестах Pages; `slow` исключается из трёх CI-гейтов и получает дом в nightly вместе с `performance`; out-of-tree элементы сбора собираются в список и выдаются предупреждением вместо тихого пропуска; из test-семейства make-таргетов снимается `--env-file`, которого не существует и который для `docker-compose.test.yml` не нужен.

## Boundaries & Constraints

**Always:**
- Явный маркер в файле побеждает автоматический — главный инвариант хука; правка его не касается.
- `backend/conftest.py` не импортирует Django и не трогает настройки: только `pytest` и stdlib.
- Состав прогонов меняется исключительно фильтрами `-m`. Тесты не переносятся, не переписываются, не удаляются.
- Любое изменение состава прогонов отражается в таблице «Где что исполняется» в `backend/docs/testing-standards.md` и `project-context.md` §4.
- Каждый исключённый из гейта класс тестов исполняется где-то ещё: «не место в обычном гейте» ≠ «не исполнять нигде».

**Ask First:**
- Замер покрытия на суженном наборе `backend-ci.yml` даёт меньше порога `--cov-fail-under=65` — доложить цифру, порог **не понижать** (запас на 2026-08-03 был ≈ 0,2 п.п.).
- Предупреждение об out-of-tree сработало на реальном прогоне пакета — значит, в проекте есть тесты вне `backend/`; доложить состав, предупреждение не глушить.

**Never:**
- Не превращать out-of-tree в `UsageError`: чужое дерево — не наша зона ответственности, обрывать чужой сбор нельзя.
- Не снимать и не переставлять маркеры `slow` и `data_dependent` на самих тестах — они ортогональны и ставятся вручную.
- Не чинить нетестовые таргеты `Makefile` (`format`, `lint`, `migrate`, `up`, `down`, `clean`) — они сломаны иначе и это отдельный долг.
- Не понижать `--cov-fail-under` ни в одном workflow.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Тест вне `backend/` | `pytest -m unit /tmp/ext/test_outside.py` | Маркер не ставится, сбор продолжается, в конце — предупреждение со списком `nodeid` и причиной «путь вне backend/» | `UserWarning`, не падение |
| Элемент сбора без пути | элемент, у которого нет ни `path`, ни `fspath` | То же предупреждение, причина «нет пути к файлу» | `UserWarning` |
| Непокрытый путь внутри `backend/` | `backend/tests/smoke/test_x.py` | Сбор прерван (поведение сохраняется) | `pytest.UsageError` со списком файлов |
| Обычный тест внутри `backend/` | `tests/integration/test_x.py` | Маркер `integration`, предупреждений нет | N/A |
| Стресс-тесты Pages | `tests/integration/test_pages_performance.py` | `performance` (явный маркер побеждает каталог `integration/`) | N/A |
| Медленный тест в `apps/` | `test_api_products.py::…_under_500ms` | Маркеры `unit` + `slow`; в PR-гейты не попадает, в nightly попадает | N/A |
| Локальный запуск перф-тестов | `make test-performance` при отсутствии `docker/.env` | Контейнеры поднимаются, прогон идёт | Нет `couldn't find env file` |

</frozen-after-approval>

## Code Map

- `backend/conftest.py:73-118` -- `_relative_parts` возвращает `None` и на «чужое дерево», и на «нет пути»; хук обе ситуации молча пропускает. Пункт 3.
- `backend/tests/unit/test_pytest_marker_autotagging.py:152-160` -- `test_item_outside_backend_is_skipped` и `test_item_without_path_is_skipped` фиксируют текущее молчание; их нужно расширить ассертом на предупреждение.
- `backend/tests/integration/test_pages_performance.py:20,247` -- два класса с явным `@pytest.mark.integration`. Пункт 1.
- `backend/apps/products/tests/test_api_products.py:247,295` -- единственные `slow` вне `tests/performance/`; получают `unit` и потому сидят в быстром гейте. Пункт 2.
- `.github/workflows/backend-ci.yml:201`, `deploy.yml:115` -- фильтр `-m "not integration and not data_dependent and not performance"` + `--cov-fail-under`.
- `.github/workflows/main.yml:123` -- фильтр `-m "not performance"`, полный набор на каждом PR.
- `.github/workflows/performance-tests.yml:91` -- nightly `-m performance`; сюда переезжает `slow`.
- `Makefile:78-108` -- `test`, `test-unit`, `test-integration`, `test-performance`, `test-fast`; `Makefile:111-120` -- `logs`, `shell`, `db-shell` (тот же сломанный вызов test-compose). Пункт 4.
- `docker/docker-compose.test.yml` -- подстановок переменных нет ни одной (проверено), `env_file` не объявлен → `--env-file` не нужен вовсе.
- `backend/docs/testing-standards.md:30-41`, `project-context.md:75-89` -- таблица «где что исполняется» и абзац про ортогональные маркеры.
- `_bmad-output/planning-artifacts/tech-debt.md:129-154` -- п. 19; `_bmad-output/implementation-artifacts/deferred-work.md:9-22` -- четыре закрываемых пункта.

## Tasks & Acceptance

**Execution:**
- [x] `backend/conftest.py` -- различить «чужое дерево» и «нет пути»: `_relative_parts` возвращает сентинел `OUTSIDE_BACKEND` вместо `None` для путей вне `BACKEND_ROOT`; хук копит такие элементы и после цикла выдаёт `warnings.warn` со списком и причиной. `UsageError` для непокрытых путей внутри `backend/` сохранён без изменений. Добавлены `UnmarkedTestWarning` и `_identify`.
- [x] `backend/tests/unit/test_pytest_marker_autotagging.py` -- `TestHook` расширен шестью тестами (out-of-tree, pathless с `nodeid` и без, одно предупреждение на весь сбор, отсутствие шума на обычном прогоне, `UsageError` не подавлен). В `TestConfigConsistency` добавлена проверка объявления `slow` и `data_dependent` в обоих `pytest.ini`. Было 39 тестов, стало 45.
- [x] `backend/tests/integration/test_pages_performance.py` -- маркеры расставлены **по методам** (уточнено ревью, см. Spec Change Log): 6 тестов с ассертом на время → `performance`, `test_cache_invalidation_accuracy_under_load` → `integration`. В docstring модуля объяснено, почему файл остаётся в `tests/integration/` и почему разметка поштучная.
- [x] `.github/workflows/backend-ci.yml`, `.github/workflows/deploy.yml`, `.github/workflows/main.yml` -- `and not slow` добавлен в фильтр `-m`, с комментарием о причине.
- [x] `.github/workflows/performance-tests.yml` -- прогон переведён на `-m "performance or slow"`, шапка и name шага поправлены.
- [x] `Makefile` -- `--env-file` снят с девяти вызовов `docker-compose.test.yml`; добавлен таргет `test-slow` + `.PHONY` + строка в `help`; над блоком — комментарий, почему `--env-file` не нужен.
- [x] `backend/docs/testing-standards.md`, `project-context.md` -- таблица «где что исполняется» обновлена, добавлены абзацы про `slow` как рычаг и про «маркер задаёт свойство теста, а не каталог».
- [x] `_bmad-output/planning-artifacts/tech-debt.md` -- в п. 19 дописан хвост с фактическими цифрами и исправлен неверный вывод 2026-08-03 про округление порога.
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- четыре пункта блока tech-debt-19 помечены закрытыми; заведена новая запись про красный порог покрытия.

**Acceptance Criteria:**
- ✅ Given рабочее дерево после правки, when выполнен `pytest --collect-only -q -m "unit or integration or performance"`, then собрано ровно столько же, сколько даёт полный `pytest --collect-only -q`. **Проверено на финальном дереве (после правок ревью):** 3017 против 3017. Инвариант перемерялся трижды по мере изменения дерева — 3006/3006, затем 3007/3007, затем 3017/3017.
- ⚠️ Given фильтр `backend-ci.yml` с `and not slow`, when выполнен прогон с покрытием, then ни один `slow`-тест и ни один тест `test_pages_performance.py` в выборку не попал, а `--cov-fail-under=65` берётся. **Первая половина выполнена** (1932 passed, 1033 deselected). **Порог не берётся — и не брался до правки:** на одном дереве 64,99 % без `and not slow` против 64,93 % с ним, оба ниже 65. Разница — 24 оператора, все до одного суть тела самих исключённых тестов (`test_api_products.py`: 197 операторов, `0` непокрытых → `24`), которые `--cov=.` держит в знаменателе; продакшен-код не потерял ничего. `backend-ci.yml` красный на `develop` с 2026-08-05 (стори 40.4) по этой же причине: `1930 passed`, `Total coverage: 64.92%`. Порог не понижался, вопрос вынесен человеку и записан в `deferred-work.md`.
- ✅ Given nightly-фильтр `-m "performance or slow"`, when выполнен сбор, then в него входят 27 перф-тестов, 2 `slow` из `apps/products/` и тайминговые тесты `test_pages_performance.py`. **Проверено:** сбор дал ровно 35 (27 + 2 + 6), прогон — `35 passed, 4 subtests passed` за 3:28. Седьмой тест Pages — `test_cache_invalidation_accuracy_under_load` — намеренно остался в PR-гейте: сбор `-m "not performance and not slow"` по этому файлу даёт ровно 1 из 7.
- ⚠️ Given временный тест вне `backend/`, when выполняется сбор, then он не размечен, сбор не прерван, а в сводке предупреждений он назван. **Выполнено с оговоркой, вскрытой ревью.** Проверено на `/tmp/exttests/test_outside.py`: при передаче вместе с внутренним путём — `UnmarkedTestWarning` с текстом `- /tmp/exttests/test_outside.py (путь вне backend/, тестов: 1)`, прогон зелёный. Но при передаче **только** внешнего пути rootdir оказывается другим, `backend/conftest.py` не загружается вовсе, и предупреждения нет — исполнить там нечего. Из conftest этот случай закрыть невозможно, нужен плагин уровня окружения. Граница задокументирована в шапке `conftest.py` и в `deferred-work.md`.
- ✅ Given отсутствующий `docker/.env`, when выполнена команда из тела таргета, then контейнеры поднимаются и прогон стартует без `couldn't find env file`. **Проверено:** все замеры этой спеки выполнены командой `docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend …` — телом починенных таргетов. Сам `make` на машине не установлен, поэтому «проверено через make» не заявляется.

## Spec Change Log

### 2026-08-06 — итерация 1, состязательное ревью (Blind Hunter + Edge Case Hunter)

**Что вскрылось (по убыванию тяжести):**

1. **Дифф одновременно утверждал и опровергал одно и то же.** `tech-debt.md` объявлял вывод «порог берётся благодаря округлению» опровергнутым, а свежие врезки в `testing-standards.md` и `project-context.md`, добавленные тем же диффом, повторяли «порог берётся впритык, запас ≈ 0,2 п.п.». Формулировка не просто устарела — она инвертировала смысл: описывала как «есть запас» ситуацию «CI красный четыре прогона подряд». Врезки переписаны на фактическое состояние.
2. **Из PR-гейтов вместе с таймингом уходила корректность.** Классовый `performance` на `test_pages_performance.py` выводил из всех гейтов и `test_cache_invalidation_accuracy_under_load`, у которого ассертов на время нет вовсе. Проверено: одиночную инвалидацию кэша покрывает `test_pages_api.py::PagesAPICachingTest`, конкурентную — больше ничто. Маркеры переставлены на методы.
3. **Ключевой сценарий пункта 3 хук не достаёт.** Проверено на месте: `pytest /tmp/ext/test_x.py` без единого пути внутри `backend/` даёт другой rootdir, `conftest.py` не загружается, предупреждения нет. Смешанные аргументы — работает. Починить это из conftest нельзя в принципе; граница задокументирована в шапке `conftest.py`, в `deferred-work.md` пункт помечен закрытым частично.
4. **`make db-shell` и `make shell` остались нерабочими,** хотя дифф правил ровно эти строки: `db-shell` ходил под `-U freesport_user -d freesport` при `postgres`/`freesport_test` в тестовом контейнере, оба использовали `exec` там, где контейнера обычно нет. Исправлено на `run --rm` и верные учётные данные.
5. **Связка «workflow ↔ маркер» не проверялась ничем.** Три workflow стали зависеть от строки `slow`; опечатка `not slo` прошла бы все гейты и молча вернула флак в PR-прогон. Добавлен класс тестов `TestCIFilters` — тот же класс ошибки, ради которого написан хук, просто переехал на уровень YAML.
6. **Смысл `slow` сузился, а его определение — нет.** В обоих `pytest.ini` он описывался как «медленные тесты»; долгий, но детерминированный тест, помеченный по старому смыслу, теперь молча исчезал бы из PR-гейтов. Описание маркера и раздел в `testing-standards.md` уточнены.

**Прочее из патч-класса:** `resolve()` мог бросить `OSError`/`RuntimeError` и оборвать весь сбор трейсбеком — ловим три типа; несколько тестов одного out-of-tree файла схлопывались в одну строку без счётчика — добавлен `Counter`; извлечение пути дублировалось в двух функциях — вынесено в `_item_path`; хардкод `{"slow", "data_dependent"}` в тесте заменён константой `ORTHOGONAL_MARKERS` в `conftest.py`; ассерты по `record[0]` не фильтровали категорию предупреждения; `PathlessItem` завязывался на `del self.nodeid`; список «осталось за объёмом» в `deferred-work.md` не называл `clean`, `createsuperuser`, `collectstatic` и неполный `.PHONY`; гарантия «в test-compose нет подстановок» держалась на комментарии — теперь на тесте.

**Решение по классификации:** переразметка `test_pages_performance.py` по методам формально отклоняется от задачи «оба класса → performance», но не от замороженного Intent («явный `performance` на стресс-тестах Pages») и прямо следует правилу этой же спеки «маркер задаёт свойство теста, а не каталог». Полный откат и передеривация ради переноса двух декораторов несоразмерны — проведено как patch с записью здесь.

**KEEP (сохранить при любой переделке):** маркеры на методах, а не на классе, у `test_pages_performance.py` — классовый маркер уже один раз увёл функциональную проверку из гейтов; граница применимости хука в шапке `conftest.py` — без неё пункт 3 выглядит закрытым полностью, каким он не является; `TestCIFilters` со `skip` при недоступности файлов — тест-контейнер монтирует только `backend/`, жёсткое падение там было бы ложным; счётчик тестов в предупреждении; `run --rm` вместо `exec` в `shell`/`db-shell`.

## Design Notes

Сентинел вместо второго `None` — чтобы «чужое дерево» и «сломался расчёт пути» перестали быть неразличимы:

```python
OUTSIDE_BACKEND = object()  # путь есть, но ведёт за пределы backend/

def _relative_parts(item):
    path = getattr(item, "path", None) or getattr(item, "fspath", None)
    if path is None:
        return None                      # у элемента сбора нет файла
    try:
        return Path(str(path)).resolve().relative_to(BACKEND_ROOT).parts
    except ValueError:
        return OUTSIDE_BACKEND           # чужое дерево — размечать нечем, но молчать нельзя
```

`warnings.warn`, а не `config.issue_config_time_warning`: хук вызывается в тестах напрямую с `config=None`, и эта развязка ценна — она позволяет проверять поведение без запуска pytest. Предупреждения, выданные из `pytest_collection_modifyitems`, попадают в стандартную сводку warnings.

`UsageError` для out-of-tree не годится: под него подпадает `--pyargs` и любой сторонний тест, переданный явным путём, — обрывать чужой сбор своим правилом нельзя.

## Verification

**Commands:** (префикс `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend`)
- `pytest tests/unit/test_pytest_marker_autotagging.py -q` -- expected: зелено; 2 теста корневого `pytest.ini` скипаются в контейнере
- `pytest --collect-only -q -m "unit or integration or performance"` и `pytest --collect-only -q` -- expected: одинаковое число тестов
- `pytest --collect-only -q -m "performance or slow"` -- expected: 36 тестов (27 + 2 + 7)
- `pytest -m "not integration and not data_dependent and not performance and not slow" --cov=. --cov-fail-under=65 -q` -- expected: зелено, процент покрытия зафиксирован и доложен
- `pytest -m "performance or slow" -q` -- expected: зелено (nightly-набор реально исполним)
- `black --check conftest.py && flake8 conftest.py --max-line-length=120 --extend-ignore=E203,W503` -- expected: без замечаний

**Manual checks:**
- `make` на машине разработчика не установлен — таргеты проверяются исполнением их тела построчно и вычиткой синтаксиса `Makefile`; факт отражается в отчёте, «проверено через make» не заявлять.
- Out-of-tree предупреждение проверяется временным файлом вне `backend/` и удаляется после проверки. **Обязательно проверить оба вызова:** только внешний путь и внешний вместе с внутренним — поведение различается.
- `TestCIFilters` и проверки корневого `pytest.ini` в тест-контейнере пропускаются (смонтирован только `backend/`). Запускать их из корня репозитория: `backend/venv/Scripts/python.exe -m pytest backend/tests/unit/test_pytest_marker_autotagging.py -q`. В контейнере — 44 passed / 12 skipped, из корня — 56 passed.

## Suggested Review Order

**Граница возможностей — прочесть до кода**

- Что хук физически не может закрыть; без этого пункт 3 выглядит закрытым полностью
  [`conftest.py:15`](../../backend/conftest.py#L15)

**Разметка вне дерева — сердце пункта 3**

- Сентинел вместо второго `None`: «чужое дерево» и «нет файла» перестали быть неразличимы
  [`conftest.py:67`](../../backend/conftest.py#L67)

- Три типа исключений: `resolve()` роняет весь сбор, если не поймать `OSError`/`RuntimeError`
  [`conftest.py:101`](../../backend/conftest.py#L101)

- Идентификация по пути, а не по `nodeid`: снаружи rootdir он вырождается в `::test_x`
  [`conftest.py:123`](../../backend/conftest.py#L123)

- Предупреждение раньше `UsageError`: сторож обрывает сбор, информация иначе теряется
  [`conftest.py:170`](../../backend/conftest.py#L170)

**Состав прогонов — здесь пряталась главная находка ревью**

- Разметка по методам: классовый маркер уводил из гейтов функциональную проверку
  [`test_pages_performance.py:185`](../../backend/tests/integration/test_pages_performance.py#L185)

- Быстрый гейт и порог покрытия, который он не берёт с 2026-08-05
  [`backend-ci.yml:203`](../../.github/workflows/backend-ci.yml#L203)

- Единственное место, где выведенное из гейтов реально исполняется
  [`performance-tests.yml:94`](../../.github/workflows/performance-tests.yml#L94)

**Сторожа против повторения той же ошибки**

- Опечатка `not slo` в YAML прошла бы все гейты — теперь нет
  [`test_pytest_marker_autotagging.py:394`](../../backend/tests/unit/test_pytest_marker_autotagging.py#L394)

- Гарантия «в test-compose нет подстановок» перестала быть обещанием в комментарии
  [`test_pytest_marker_autotagging.py:402`](../../backend/tests/unit/test_pytest_marker_autotagging.py#L402)

- Один список маркеров, от которого зависят фильтры CI
  [`conftest.py:47`](../../backend/conftest.py#L47)

**Makefile**

- Почему `--env-file` снят, а не поправлен на `../.env`
  [`Makefile:78`](../../Makefile#L78)

- Ревью показало, что снятия мало: неверные учётные данные и `exec` без контейнера
  [`Makefile:137`](../../Makefile#L137)
