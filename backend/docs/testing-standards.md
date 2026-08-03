# Стандарты тестирования Backend (FREESPORT)

## Маркеры pytest

**Маркер определяется каталогом теста и проставляется автоматически — руками писать не нужно.**
Разметку делает хук `pytest_collection_modifyitems` в `backend/conftest.py`.

**Категорию задаёт каталог-категория в пути.** Ищется самый глубокий; работает на любой глубине, поэтому `tests/integration/`, `apps/products/tests/integration/` и `apps/products/api/tests/integration/` размечаются одинаково.

| Каталог-категория в пути | Маркер |
|---|---|
| `unit/` | `unit` |
| `integration/` | `integration` |
| `functional/` | `integration` |
| `regression/` | `integration` |
| `performance/` | `performance` |

**Если каталога-категории в пути нет**, применяется умолчание: всё под `apps/` — `unit` (включая `apps/<app>/tests.py` в стиле Django). Для `tests/` умолчания нет.

> ⚠️ Отсюда осознанная асимметрия: новый каталог под `tests/` без категории обрывает сбор, а под `apps/` — молча получает `unit`. Так сделано потому, что тесты приложения лежат рядом с кодом и по умолчанию модульные; требовать каталог-категорию во всех `apps/*/tests/` означало бы перетасовать полсотни существующих файлов. Если тест в приложении не модульный — положите его в `tests/integration/` или `tests/performance/` внутри приложения, либо поставьте маркер явно.

**Явный маркер в файле переопределяет автоматический.** `@pytest.mark.integration` или `pytestmark = [pytest.mark.integration, ...]` — хук такой тест не тронет.

**Маркер `unit` означает «модульный тест приложения», а не «без БД».** Тест с `django_db` внутри `apps/` штатно получает `unit`.

**Путь без категории и без умолчания обрывает сбор** с `pytest.UsageError`, перечисляющей файлы. Это сторож, а не дефект: он заменяет собой отдельную CI-проверку полноты разметки — полный сбор пакета занимает ~6 минут, гонять его дважды в каждом PR ради той же проверки смысла нет. Сторож глобален: он срабатывает независимо от `-k` и `-m`, потому что хук выполняется до отбора. Служебные и временные каталоги должны быть в `norecursedirs` (объявлен в обоих `pytest.ini` — корневом и `backend/`), иначе случайный файл заблокирует весь прогон.

Почему так: до появления хука 852 из 2699 тестов (31 %) не имели ни одного маркера и молча выпадали из `make test-unit` / `make test-integration`. Это дало ложно-зелёный результат на стори `security-wholesale-price-visibility` при пяти реально сломанных тестах. Правило было записано в документации, но ничем не обеспечено; вариант «проставить маркеры руками в ~100 файлах» отклонён — он не защищает от повторного накопления.

Маркеры `data_dependent` (тесты на реальных выгрузках 1С) и `slow` ортогональны автоматическим и ставятся вручную.

**Где что исполняется:**

| Прогон | Состав |
|---|---|
| `backend-ci.yml` (push/PR в `main`, `develop`) | `-m "not integration and not data_dependent and not performance"` — быстрый unit-гейт, он же считает покрытие |
| `main.yml` (push/PR в `main`, `develop`) | весь набор без `performance` — именно он ловит регрессии в интеграционных тестах |
| `performance-tests.yml` | `-m performance`, ежедневно по расписанию + вручную |
| `make test-unit` / `test-integration` / `test-performance` | по одному маркеру локально |

Правило проверяется `backend/tests/unit/test_pytest_marker_autotagging.py` — без сбора пакета. Там же обход реального дерева: любой тестовый файл, оказавшийся вне правил, валит этот тест за миллисекунды, а не полный прогон в CI.

## Сценарии тестирования: Master / Suborder flow

### Order Numbering

| Сценарий | Ожидаемый результат | Тип теста |
|----------|---------------------|-----------|
| Генерация master-номера при валидном `customer_code` | Канонический номер `CCCCCYYNNN` создан, счётчик инкрементирован | Unit |
| Отсутствие `customer_code` у пользователя | `OrderNumberError` → `ValidationError` (400) | Integration |
| Переполнение sequence (999 → 1000) | `OrderNumberSequenceExhausted` → 400, rollback | Unit |
| Форматирование master / suborder | UI-формат `CCCC-YYNNN` и `CCCCC-YYNNN-S` | Unit |
| Нормализация поиска | UI-ввод `4620-26007` → канонический `0462026007` | Unit |

### Email и Notifications

| Сценарий | Ожидаемый результат | Тип теста |
|----------|---------------------|-----------|
| Checkout с 2 suborders | Ровно 1 customer email + 1 admin email (master only) | Integration |
| Items в customer email | Все items из обоих suborders агрегированы через helper | Unit |
| Suborder save | Не ставит email задачи в очередь | Unit |

### Permissions

| Сценарий | Ожидаемый результат | Тип теста |
|----------|---------------------|-----------|
| Anonymous `POST /api/orders/` | **401 Unauthorized** | Integration |

### Admin

| Сценарий | Ожидаемый результат | Тип теста |
|----------|---------------------|-----------|
| `items_count` для master с suborders | Сумма позиций из всех suborders | Unit |
| `total_items_quantity` для master | Сумма количеств из всех suborders | Unit |
| N+1 prevention | `prefetch_related("sub_orders__items")` используется | Unit |
