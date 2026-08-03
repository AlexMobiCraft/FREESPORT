# Стандарты тестирования Backend (FREESPORT)

## Маркеры pytest

**Маркер определяется каталогом теста и проставляется автоматически — руками писать не нужно.**
Разметку делает хук `pytest_collection_modifyitems` в `backend/conftest.py`, таблица соответствия — константа `PATH_RULES` там же.

| Каталог | Маркер |
|---------|--------|
| `apps/*/tests/integration/` | `integration` |
| `apps/**` (всё остальное, включая `apps/<app>/tests.py`) | `unit` |
| `tests/unit/` | `unit` |
| `tests/integration/` | `integration` |
| `tests/functional/` | `integration` |
| `tests/regression/` | `integration` |
| `tests/performance/` | `performance` |

Порядок правил значим: первое совпадение выигрывает, поэтому специфичное `apps/*/tests/integration/` стоит раньше общего `apps/`.

**Явный маркер в файле переопределяет автоматический.** Если тест внутри `apps/` по сути интеграционный, поставьте `@pytest.mark.integration` или `pytestmark = [pytest.mark.integration, ...]` — хук такой тест не тронет.

**Новый тестовый каталог требует правила.** Путь, не покрытый `PATH_RULES`, обрывает сбор с `pytest.UsageError`, перечисляющей файлы. Это сторож, а не дефект: он и заменяет собой отдельную CI-проверку полноты разметки. Полный сбор пакета занимает ~7,5 минут — гонять его дважды в каждом PR ради той же проверки смысла нет.

Почему так: до появления хука 852 из 2699 тестов (31 %) не имели ни одного маркера и молча выпадали из `make test-unit` / `make test-integration`. Это дало ложно-зелёный результат на стори `security-wholesale-price-visibility` при пяти реально сломанных тестах. Правило было записано в документации, но ничем не обеспечено; вариант «проставить маркеры руками в ~100 файлах» отклонён — он не защищает от повторного накопления.

Маркеры `data_dependent` (тесты на реальных выгрузках 1С) и `slow` ортогональны автоматическим и ставятся вручную.

Перф-тесты выведены из обычного гейта: `-m "not performance"` в `backend-ci.yml`, `deploy.yml`, `main.yml`. Точка входа — `make test-performance`.

Правило проверяется `backend/tests/unit/test_pytest_marker_autotagging.py` — без сбора пакета.

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
