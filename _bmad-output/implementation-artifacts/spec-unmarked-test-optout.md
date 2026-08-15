---
title: 'Честный текст гейта неразмеченных тестов'
type: 'chore'
created: '2026-08-14'
status: 'done'
review_loop_iteration: 1
context: []
baseline_commit: 'ba52e28b560b795dabfb51d91d418d3b4ac83070'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** При обрыве сбора гейт неразмеченных тестов советует «Либо уберите отбор, если прогон и должен быть полным» (`backend/conftest.py:243`) — как универсальный выход. В CI этот выход неприменим: состав фильтров всех четырёх прогонов задан явно и застережён тестами — `test_pr_gates_exclude_performance_and_slow` держит три PR-гейта, `test_nightly_runs_what_pr_gates_dropped` — nightly. Человек, читающий лог CI, получает совет, запрещённый собственными тестами проекта.

**Approach:** Уточнить формулировку так, чтобы снятие отбора подавалось как локальный выход, а невозможность этого в CI была названа прямо. Записать в `backend/docs/testing-standards.md` ограничение: для теста из установленного пакета (`--pyargs`) в пределах одного вызова pytest остаётся единственный рычаг — `-m`; развести чужой пакет и `backend/` по двум вызовам можно ценой отсутствия общего прогона. Закрепить новый текст тестом. Механизм опт-аута не строить.

## Boundaries & Constraints

**Always:**
- В `backend/conftest.py` — только pytest и stdlib; импорты Django и обращение к настройкам запрещены (файл грузится раньше `settings.configure()`).
- Комментарии, docstrings и документация — на русском.
- Меняется только текст сообщения. Условие срабатывания гейта (`dropped and _markexpr(config)`), состав `_advice`, `_warning_text`, `_unmapped_text` и поведение мягкого режима остаются как есть.
- Перед правкой символа — `npx gitnexus impact <symbol> --direction upstream`; перед коммитом — `npx gitnexus detect-changes --scope all`.
- Работа в ветке `chore/unmarked-test-gate-message` (создана от `develop`).

**Ask First:**
- Любое изменение поведения гейта, а не текста.
- Любая правка `pytest.ini` или workflow-файлов.

**Never:**
- Не добавлять ini-опцию `unmarked_allow` (вариант A) — решение Alex 2026-08-14: вариант C.
- Не добавлять переменную окружения для отключения гейта (вариант B отвергнут окончательно: бесшумное отключение в CI без следа в диффе).
- Не брать прицепом задачи из `intent-conftest-path-classification.md` (третий сентинел для `OSError`, сверка по `nodeid`) — решение Alex: отдельная работа.
- Не трогать незакоммиченный автоблок GitNexus в `AGENTS.md` / `CLAUDE.md`.

## I/O & Edge-Case Matrix

| Сценарий | Вход / состояние | Ожидаемое поведение | Обработка ошибок |
|---|---|---|---|
| Гейт сработал, текст честен | неразмечаемый элемент, `markexpr="unit"`, элемент выпал из `items` | `UsageError`; в тексте снятие отбора помечено как локальный выход, и прямо сказано, что в CI его нет | N/A |
| Регресс формулировки | тот же | В тексте нет безусловного «Либо уберите отбор, если прогон и должен быть полным» | N/A |
| Совет по причине не потерян | в `dropped` есть элемент с `REASON_OUTSIDE` | Совет «перенесите его под backend/ или поставьте маркер в файле явно» остаётся на месте | N/A |
| Мягкий режим не затронут | `markexpr=""` либо отрицательное выражение | `UnmarkedTestWarning`, текст `_warning_text` без изменений | N/A |

</frozen-after-approval>

## Code Map

- `backend/conftest.py` — `_gate_text`:231 (правится строка 243); `_advice`:209 и `_join`:226 — соседи, не трогаются; хук:310, вызов `_gate_text` — :339.
- `backend/tests/unit/test_pytest_marker_autotagging.py` — `TestDeselectGate`:320; образец нового теста — `test_gate_message_does_not_blame_markexpr`:341; хелперы `run_hook`:93 и `outside_item`:127.
- `backend/docs/testing-standards.md` — раздел «Тест вне дерева `backend/`»:28; вставка после абзаца «Одного деселекта тоже мало»:42.
- `_bmad-output/implementation-artifacts/deferred-work.md` — запись об отсутствии опт-аута:640-643; стиль закрытия — записи :619 и :645.

## Tasks & Acceptance

**Execution:**
- [x] `backend/conftest.py` — в `_gate_text` заменить безусловный совет о снятии отбора на формулировку, разделяющую локальный прогон и CI — чтобы сообщение не предлагало читателю лога CI действие, запрещённое тестом `test_pr_gates_exclude_performance_and_slow`.
- [x] `backend/tests/unit/test_pytest_marker_autotagging.py` — добавить в `TestDeselectGate` тест на новый текст по образцу `test_gate_message_does_not_blame_markexpr` — иначе формулировка ничем не закреплена и вернётся при следующей правке.
- [x] `backend/docs/testing-standards.md` — в раздел «Тест вне дерева `backend/`» добавить абзац об отсутствии опт-аута и о тупике при `--pyargs`, с обоснованием, почему механизм не построен — сейчас документация об этом молчит.
- [x] `_bmad-output/implementation-artifacts/deferred-work.md` — закрыть запись об отсутствии опт-аута (:640-643) в стиле соседних закрытых записей, с блоком «Как закрыт».

**Acceptance Criteria:**
- Given гейт сработал и текст сообщения получен, when читатель ищет в нём выход, then снятие отбора названо локальным выходом, а невозможность этого в CI — названа прямо.
- Given правка `_gate_text` внесена, when прогоняется `TestDeselectGate` целиком, then все существующие тесты класса проходят без изменений (ни один из них текущую формулировку не проверяет).
- Given документация прочитана, when разработчик встретил тест из установленного пакета, then он находит записанное ограничение и знает, что обходного пути нет, а не гадает.
- Given полный unit-прогон, when он завершается, then результат не хуже эталона `2027 passed, 17 skipped, 0 failed` плюс один новый тест.

## Spec Change Log

### Итерация 1 — 2026-08-15, по итогам ревью

**Находка (intent_gap, разрешена Alex):** Approach предписывал записать, что при `--pyargs` «обходного пути нет вовсе». Утверждение ложно: блок «ГРАНИЦА ВОЗМОЖНОСТЕЙ» (`backend/conftest.py:16-20`) документирует, что вызов без единого пути внутри `backend/` даёт другой rootdir, корневой conftest не загружается и хук не исполняется. Правка, вся суть которой — перестать врать в сообщении, писала бы новую неправду в документацию.
**Что изменено:** Approach сужен до «в пределах одного вызова pytest остаётся единственный рычаг `-m`; развести по двум вызовам можно ценой отсутствия общего прогона». Решение Alex 2026-08-15 из трёх вариантов (сузить / убрать абзац / оставить).

**Находка (patch):** Problem утверждал, что состав всех четырёх прогонов застережён тестом `test_pr_gates_exclude_performance_and_slow`. Тест параметризован по `PR_GATES = ("backend-ci.yml", "deploy.yml", "main.yml")` — три workflow; nightly стережёт `test_nightly_runs_what_pr_gates_dropped`. Найдено обоими ревьюерами независимо.
**Что изменено:** названы оба теста с указанием, что какой держит. Правка frozen-блока санкционирована Alex 2026-08-15.

**Известно-плохое состояние, которого избегаем:** документация и docstring, ссылающиеся на один тест как на страховку четырёх прогонов, и абзац, объявляющий тупиком случай, для которого в том же репозитории описан обход.

**KEEP (обязано пережить перевывод):** правится только строковый литерал в `_join` и docstring `_gate_text` — условие `dropped and _markexpr(config)`, состав `_advice`, `_warning_text`, `_unmapped_text` и мягкий режим не трогаются. Два смысловых якоря сообщения — «локально» и «в CI … нет» — и опора теста именно на них. Порядок кусков в `_join`: совет по причине первым, ссылка на документацию последней.

## Design Notes

Целевая правка `backend/conftest.py:241-245` — одна строка списка `_join`:

```python
    tail = _join(
        _advice(dropped),
        "Локально помогает и снятие отбора: без `-m` собирается всё. В CI такого выхода нет — "
        "состав фильтров там зафиксирован и застережён тестом.",
        "См. backend/docs/testing-standards.md, раздел «Маркеры pytest».",
    )
```

Точная редакция может отличаться; обязательны два смысловых якоря — «локально» и «в CI … нет», — и на них же опирается тест. Порядок кусков в `_join` не меняется: совет по причине идёт первым, ссылка на документацию — последней.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -v tests/unit/test_pytest_marker_autotagging.py` — ожидается: все тесты файла зелёные, новый тест присутствует в выводе.
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q -m unit` — ожидается: `0 failed`, число passed не ниже 2027 + 1 новый.
- `npx gitnexus detect-changes --scope all` — ожидается: затронут только `_gate_text`.

Путь внутри контейнера — от `/app`. `--env-file` тестовому compose не передавать. После прогонов — `docker compose -p freesport-test -f docker-compose.test.yml down`.

## Suggested Review Order

**Сама формулировка**

- Единственная содержательная правка: снятие отбора разведено на локальное и CI.
  [`conftest.py:249`](../../backend/conftest.py#L249)

- Почему выход назван локальным; здесь же названы оба страхующих теста, а не один.
  [`conftest.py:241`](../../backend/conftest.py#L241)

- Контекст: гейт требует обоих условий сразу — правка его не касается.
  [`conftest.py:338`](../../backend/conftest.py#L338)

**Записанное ограничение**

- Три локальных выхода вместо «ровно одного»; в CI не работает ни один.
  [`testing-standards.md:44`](../../backend/docs/testing-standards.md#L44)

- Случай `--pyargs`: тупик сужен до одного вызова pytest — обход через смену rootdir существует.
  [`testing-standards.md:46`](../../backend/docs/testing-standards.md#L46)

- Обоснование, почему механизм опт-аута не построен; отказ от переменной окружения.
  [`testing-standards.md:48`](../../backend/docs/testing-standards.md#L48)

- Опровержение «тупика» живёт здесь — блок, с которым сверялась формулировка выше.
  [`conftest.py:16`](../../backend/conftest.py#L16)

**Периферия**

- Тест, закрепляющий оба якоря и отсутствие прежней безусловной фразы.
  [`test_pytest_marker_autotagging.py:356`](../../backend/tests/unit/test_pytest_marker_autotagging.py#L356)

- Страхующий тест, на который ссылается сообщение: параметризован по трём workflow.
  [`test_pytest_marker_autotagging.py:646`](../../backend/tests/unit/test_pytest_marker_autotagging.py#L646)

- Закрытие записи реестра плюс три новые defer-записи по итогам ревью.
  [`deferred-work.md:640`](deferred-work.md#L640)
