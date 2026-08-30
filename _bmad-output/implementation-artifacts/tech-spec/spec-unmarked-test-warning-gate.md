---
title: 'UnmarkedTestWarning как гейт по факту деселекта'
type: 'chore'
created: '2026-08-14'
status: 'done'
baseline_commit: '07b2c3b35f9c53a6ae7aa24ba825b27802a987cf'
review_loop_iteration: 1
context:
  - '{project-root}/_bmad-output/implementation-artifacts/intent-unmarked-test-warning-gate.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Тесту, которому авторазметка не может проставить маркер (путь вне `backend/`, элемент сбора без файла), хук `backend/conftest.py` выдаёт `UnmarkedTestWarning`. Предупреждение не влияет на код возврата, тонет в общей сводке и глушится `--disable-warnings` / `-p no:warnings`, поэтому при отборе по маркеру такой тест выпадает из прогона молча — ровно то, ради предотвращения чего хук написан.

**Approach:** Хук поднимает `pytest.UsageError` вместо предупреждения, когда **задан явный `-m` И неразмечаемый элемент действительно деселектнут** этим выражением. Факт деселекта определяется наблюдением, а не предсказанием: хук становится обёрткой (`hookwrapper`), размечает до отбора и сверяет состав `items` после него.

**Почему не «просто непустой `-m`»** (пересмотр решения от 2026-08-13, Alex, 2026-08-14): неразмеченный тест выпадает только при **положительном** выражении. При отрицательном он проходит фильтр и исполняется — а это три из четырёх прогонов CI (`backend-ci`, `main`, `deploy` используют `-m "not ..."`). Гейт на «непустой `-m`» рвал бы их сбор ошибкой «тесты выпадают из отбора», ложной ровно в этой ситуации. Проверено экспериментально: `-m "not slow"` на файле без маркеров → тест собран и исполнен.

Отвергнутые альтернативы (не предлагать заново): `filterwarnings` в обоих `pytest.ini`; `-W error::` в CI-вызовах; CI-шаг с `grep`; вычисление положительности выражения через приватный `_pytest.mark.expression`.

## Boundaries & Constraints

**Always:**
- В `backend/conftest.py` — только pytest и стандартная библиотека. Импорт Django и обращение к настройкам запрещены: файл загружается раньше `backend/tests/unit/conftest.py`, который вызывает `settings.configure()`.
- Комментарии и docstrings — на русском.
- Гейт требует **обоих** условий: непустой `markexpr` **и** фактический деселект конкретного элемента. Одного деселекта мало — `-k` без `-m` гейт не включает.
- Разметка выполняется до отбора. Обёртка это обеспечивает сама (её часть до `yield` идёт раньше всех обычных реализаций, включая деселект `_pytest.mark`), поэтому `tryfirst` перестаёт быть нужен — но порядок обязан сохраниться.
- Текст ошибки/предупреждения обязан соответствовать причине: совет «перенесите файл под `backend/`» неприменим к элементу, у которого файла нет вовсе.

**Ask First:**
- Правка `.github/workflows/*` — признак, что реализация пошла не туда.
- Расширение гейта на `-k`, `--deselect` или другие способы отбора.

**Never:**
- Не трогать `pytest.UsageError` для непокрытых путей **внутри** `backend/` — он срабатывает всегда, независимо от `-m` и от деселекта, и остаётся в части до `yield`.
- Не отменять асимметрию «внутри рвём сбор, снаружи мягче» как принцип.
- Не пытаться закрыть случай `pytest /tmp/ext/test_x.py` без единого пути внутри `backend/`: conftest там не загружается (см. `backend/conftest.py:15-19`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Гейт срабатывает | `-m unit`, среди items — тест вне `backend/`; после отбора он исчез | `UsageError` с перечнем выпавших и числом тестов; код возврата 4 | Не глушится `--disable-warnings` / `-p no:warnings` |
| Отрицательное выражение | `-m "not performance and not slow"`, тот же тест уцелел после отбора | `UnmarkedTestWarning`, сбор продолжается, прогон зелёный | N/A |
| Без `-m` | Тот же тест, отбора нет | `UnmarkedTestWarning`, сбор продолжается | N/A |
| Отбор без `-m` | `-k something`, неразмечаемый тест деселектнут по имени | Предупреждение, не ошибка — гейт требует непустой `markexpr` | N/A |
| Непокрытый путь внутри | Путь внутри `backend/` без правила разметки, любой режим | `UsageError` до отбора — существующее поведение без изменений | N/A |
| Обе беды сразу | Неразмечаемый тест + непокрытый путь внутри | Ошибка про непокрытый путь; перечень неразмечаемых не теряется — выдаётся предупреждением до неё | N/A |
| Элемент без файла | Item без `path`/`fspath`, деселектнут при `-m` | `UsageError`, но текст без совета «перенесите файл» | N/A |
| Пустой / пробельный `-m` | `-m ""` или `-m "   "` | Считается «отбора нет» → режим предупреждения | N/A |
| Config недоступен | `config` без `option` | Режим предупреждения; сбор не падает `AttributeError` | Компромисс назван в комментарии |

</frozen-after-approval>

## Code Map

- `backend/conftest.py` — вся логика. Сейчас: `UnmarkedTestWarning`:70, `_relative_parts`:101 (возвращает `OUTSIDE_BACKEND` в т. ч. при `OSError`), `_identify`:123, `@pytest.hookimpl(tryfirst=True)`:139, хук:140, `warnings.warn`:175, `raise pytest.UsageError`:189 (сторож для путей внутри — не трогать).
- `backend/tests/unit/test_pytest_marker_autotagging.py` — тесты. `FakeItem`:46, `unmarked_warnings`:71, `TestHook`:146, `TestConfigConsistency`:293 (читает оба `pytest.ini` через `configparser` — сюда же тест про `addopts`), `TestCIFilters`:349.
- `pytest.ini`, `backend/pytest.ini` — `addopts` отсутствует в обоих; это надо не только заявить, но и застеречь тестом.
- `backend/docs/testing-standards.md` — раздел «Маркеры pytest». Строка 26 утверждает «сторож срабатывает независимо от `-k` и `-m`» — после правки это верно только для путей внутри `backend/`, фразу надо уточнить, а не компенсировать врезкой ниже.
- `project-context.md` §4 (строка 80) — описывает мягкое поведение.
- `_bmad-output/implementation-artifacts/deferred-work.md`:620 — запись об этой задаче.
- `Makefile`:85-122 — `test-unit/-integration/-performance/-slow` идут с `-m`; **`test` и `test-fast` — без `-m`**.

## Tasks & Acceptance

**Execution:**
- [x] `backend/conftest.py` -- вынести разметку и сбор перечней в чистую функцию, отделив её от хука -- логика должна тестироваться без запуска pytest, иначе новые тесты упрутся в протокол обёртки
- [x] `backend/conftest.py` -- превратить хук в обёртку: до `yield` — разметка, накопление неразмечаемых элементов и существующий `UsageError` для непокрытых путей внутри `backend/`; после `yield` — сверка, какие из неразмечаемых исчезли из `items` -- деселект наблюдается, а не предсказывается по виду выражения
- [x] `backend/conftest.py` -- гейт при непустом `markexpr` (с `.strip()`) И непустом списке выпавших; иначе `UnmarkedTestWarning` -- два условия вместо одного закрывают ложное срабатывание на отрицательных выражениях
- [x] `backend/conftest.py` -- развести текст по причине: для элемента без файла убрать совет «перенесите файл»; в docstring `_markexpr` не утверждать, что `-m` приходит только из командной строки (есть `PYTEST_ADDOPTS`) -- диагностика при обрыве сбора это единственный канал связи с разработчиком
- [x] `backend/conftest.py` -- обновить docstring модуля: развилка описывается через «тест реально выпал из отбора», а не «задан `-m`» -- шапка не должна расходиться с кодом
- [x] `backend/tests/unit/test_pytest_marker_autotagging.py` -- покрыть чистую функцию и режимы по I/O-матрице, включая отрицательное выражение с неразмечаемым элементом -- именно эта комбинация была дырой в прошлой реализации
- [x] `backend/tests/unit/test_pytest_marker_autotagging.py` -- добавить тесты на реальном подпроцессном запуске pytest: (а) `-m unit` + внешний файл при `--disable-warnings -p no:warnings` → ненулевой код возврата; (б) `-m "not slow"` + тот же файл → код 0 -- порядок хуков, факт деселекта и неглушимость нельзя проверить подставным config
- [x] `backend/tests/unit/test_pytest_marker_autotagging.py` -- в `TestConfigConsistency` добавить тест: `addopts` отсутствует в обоих `pytest.ini` -- появление `addopts = -m ...` бесшумно включило бы гейт на каждом прогоне
- [x] `backend/docs/testing-standards.md` -- описать развилку; уточнить строку 26; в перечне `make`-целей не приписывать `-m` целям `test` и `test-fast` -- обе идут без него
- [x] `project-context.md` -- привести §4 в соответствие
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` -- отметить запись :620 закрытой; отдельными записями зафиксировать отложенное (см. Design Notes)

**Acceptance Criteria:**
- Given `-m unit` и собранный тест вне `backend/`, when прогон выполнен с `--disable-warnings -p no:warnings`, then код возврата ненулевой, а в выводе — перечень выпавших тестов.
- Given `-m "not performance and not slow"` и тот же тест, when прогон выполнен, then он завершается успешно, тест исполняется, выдаётся предупреждение — сбор не рвётся.
- Given отсутствие `-m`, when собран тот же тест, then поведение прежнее: одно предупреждение на весь сбор, сбор продолжается.
- Given непокрытый путь внутри `backend/`, when задан любой режим, then сбор рвётся `UsageError` как и до правки, а перечень неразмечаемых тестов при этом не теряется.
- Given весь существующий набор тестов, when выполнен `-m unit` в Docker, then результат не хуже, чем до правки (2010 passed на baseline).

## Spec Change Log

- **Итерация 1 (2026-08-14).** Находка обоих ревьюеров, подтверждённая экспериментом: гейт на условии «непустой `markexpr`» срабатывал там, где тест не выпадает — при отрицательных выражениях, то есть в `backend-ci`, `main` и `deploy`. Диагностика при этом утверждала заведомо ложное («тесты выпадают из отбора»). Корень был в запертом блоке: правило шире собственного обоснования. **Изменено:** условие гейта переписано с предсказания на наблюдение фактического деселекта (обёртка вокруг хука); в I/O-матрицу добавлены строки для отрицательного выражения и для `-k` без `-m`. **Избегаемое состояние:** реализация, ложно обрывающая три из четырёх прогонов CI. **KEEP:** структура тестов с подставным config для чистой логики; единый перечень с числом тестов на файл; сохранение мягкого режима без `-m` как опорной асимметрии; неприкосновенность `UsageError` для путей внутри `backend/`.

## Design Notes

Механизм проверен на стеке проекта (pytest 9.1.1, pluggy 1.6.0): часть обёртки до `yield` выполняется раньше деселекта `_pytest.mark`, часть после — видит уже отфильтрованный `items` (список мутируется на месте).

```python
@pytest.hookimpl(hookwrapper=True)
def pytest_collection_modifyitems(config, items):
    unmarkable = _apply_markers(items)   # разметка + UsageError для путей внутри backend/
    yield                                # здесь отрабатывает отбор по -m
    survived = {id(item) for item in items}
    dropped = [item for item in unmarkable if id(item) not in survived]
```

Проверено экспериментально: `-m unit` → выпало 1, `UsageError`; `-m "not slow"` → выпало 0, прогон зелёный; без `-m` → выпало 0.

Логику разметки держать в чистой функции, а обёртку — тонкой: протокол генератора неудобно вызывать из теста напрямую, поэтому всё, что можно, проверяется без запуска pytest, а сам факт деселекта и код возврата — подпроцессным прогоном.

**Отложить в `deferred-work.md` (не делать здесь):** (1) `_relative_parts` возвращает `OUTSIDE_BACKEND` и при `OSError`/`RuntimeError`, поэтому файл **внутри** `backend/` с нерезолвимым путём (петля симлинков, MAX_PATH на Windows) получает причину «путь вне backend/» — под гейтом это обрывает прогон с неверной диагностикой; (2) нет легального опт-аута для чужого теста, приехавшего через `--pyargs`: переносить некуда, маркер поставить нельзя, `-m` в CI не убрать.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -v tests/unit/test_pytest_marker_autotagging.py` -- expected: зелёный, включая подпроцессные тесты. `--env-file` не передавать.
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q -m unit` -- expected: не хуже baseline (2010 passed, 16 skipped, 1023 deselected).
- Ручная проверка отрицательного выражения: прогон с `-m "not performance and not slow"` и файлом вне `backend/` -- expected: код 0, тест исполнен, предупреждение выдано.
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml down` -- expected: контейнеры остановлены.
- `npx gitnexus detect-changes --scope all` -- expected: затронут только хук и новые вспомогательные функции.

## Suggested Review Order

**Сердце изменения: как определяется, что тест выпал**

- Точка входа: обёртка вместо обычного хука — до `yield` разметка, после `yield` сверка состава
  [`conftest.py:310`](../../backend/conftest.py#L310)

- Сторож для путей внутри `backend/` намеренно до `yield`: падение чужого хука не должно его отменять
  [`conftest.py:314`](../../backend/conftest.py#L314)

- Сверка по `id()` и инвариант, на котором держится её корректность
  [`conftest.py:324`](../../backend/conftest.py#L324)

- Два условия гейта: отбор задан И элемент реально выпал
  [`conftest.py:338`](../../backend/conftest.py#L338)

**Диагностика — единственный канал связи при обрыве сбора**

- Причину выпадения не называем: при `-m unit --lf` виноват мог быть не маркер
  [`conftest.py:231`](../../backend/conftest.py#L231)

- Текст мягкого режима зависит от факта выпадения, иначе он врал бы в ветке `-k`
  [`conftest.py:261`](../../backend/conftest.py#L261)

- Защитное чтение `markexpr` с проверкой типа; компромисс назван вслух
  [`conftest.py:142`](../../backend/conftest.py#L142)

- Логика разметки вынесена из хука, чтобы тестироваться без протокола обёртки
  [`conftest.py:161`](../../backend/conftest.py#L161)

**Тесты: что проверяется без pytest, а что только настоящим прогоном**

- Хелпер, играющий роль pluggy: отбор эмулируется между половинами обёртки
  [`test_pytest_marker_autotagging.py:93`](../../backend/tests/unit/test_pytest_marker_autotagging.py#L93)

- Ключевой случай: отрицательное выражение неразмеченный тест пропускает
  [`test_pytest_marker_autotagging.py:360`](../../backend/tests/unit/test_pytest_marker_autotagging.py#L360)

- Регрессионный сторож: сторож `unmapped` переживает падение нижележащего хука
  [`test_pytest_marker_autotagging.py:477`](../../backend/tests/unit/test_pytest_marker_autotagging.py#L477)

- Подпроцессный прогон: код возврата и неглушимость подставным config не проверить
  [`test_pytest_marker_autotagging.py:694`](../../backend/tests/unit/test_pytest_marker_autotagging.py#L694)

- Сторож против `addopts`: его появление бесшумно включило бы гейт навсегда
  [`test_pytest_marker_autotagging.py:562`](../../backend/tests/unit/test_pytest_marker_autotagging.py#L562)

**Документация**

- Новый раздел с таблицей развилки и оговоркой про `-k`/`--lf`
  [`testing-standards.md:28`](../../backend/docs/testing-standards.md#L28)

- Уточнение старой фразы «сторож срабатывает независимо от `-m`» — теперь она про сторож внутри дерева
  [`testing-standards.md:26`](../../backend/docs/testing-standards.md#L26)

- Выжимка для context window
  [`project-context.md:80`](../../project-context.md#L80)

- Закрытая запись плюс четыре новых отложенных пункта из ревью
  [`deferred-work.md:619`](deferred-work.md#L619)
