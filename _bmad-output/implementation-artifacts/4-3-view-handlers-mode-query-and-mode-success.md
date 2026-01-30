# Story 4.3: View-обработчики mode=query и mode=success

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **1С система**,
I want **запрашивать заказы через mode=query и подтверждать получение через mode=success**,
So that **заказы передаются по стандартному протоколу обмена с гарантией доставки**.

## Acceptance Criteria

1. **AC1:** В `ICExchangeView` реализован метод `handle_query` для обработки `GET /?mode=query`.
2. **AC2:** `handle_query` возвращает XML с неотправленными заказами (sent_to_1c=False), используя `OrderExportService`.
3. **AC3:** Если передан параметр `zip=yes`, XML упаковывается в ZIP-архив (Content-Type: application/zip).
4. **AC4:** В `ICExchangeView` реализован метод `handle_success` для обработки `GET /?mode=success`.
5. **AC5:** `handle_success` помечает все выгруженные заказы как отправленные (`sent_to_1c=True`, `sent_to_1c_at=now()`).
6. **AC6:** Копии сгенерированных файлов (XML/ZIP) сохраняются в `MEDIA_ROOT/1c_exchange/logs/` для аудита.
7. **AC7:** Integration-тесты проверяют полный цикл: получение XML, получение ZIP, подтверждение успеха.
8. **AC8:** Реализация совместима с существующей аутентификацией `checkauth`.

## Tasks / Subtasks

- [ ] Task 1: Подготовка инфраструктуры логирования (AC: 6)
  - [ ] 1.1: Убедиться, что директория `MEDIA_ROOT/1c_exchange/logs/` существует (создавать динамически).
  - [ ] 1.2: Создать хелпер `_save_exchange_log(filename, content, is_binary=False)` в `views.py` или утилитах.

- [ ] Task 2: Реализация `handle_query` (AC: 1, 2, 3)
  - [ ] 2.1: Добавить обработку `mode=query` в метод `get()` класса `ICExchangeView`.
  - [ ] 2.2: В `handle_query`: 
      - Зафиксировать текущее время `query_time`.
      - Сохранить `request.session['last_1c_query_time'] = query_time` (для Task 3).
      - Выбрать заказы `Order.objects.filter(sent_to_1c=False, created_at__lte=query_time)` с `prefetch_related`.
  - [ ] 2.3: Вызвать `OrderExportService.generate_xml(orders)`.
  - [ ] 2.4: Если заказов нет, вернуть пустой `CommmerceInfo` или корректный пустой ответ (проверить спецификацию, обычно пустой container).
  - [ ] 2.5: Обработка `zip=yes`:
      - Создать in-memory zip (io.BytesIO).
      - Записать XML в архив как `orders.xml`.
      - Вернуть `HttpResponse` с content-type `application/zip` и заголовком `filename=orders.zip`.
  - [ ] 2.6: Если `zip=no` (по умолчанию), вернуть XML (`application/xml`).
  - [ ] 2.7: Сохранить копию ответа в лог (Task 1).

- [ ] Task 3: Реализация `handle_success` (AC: 4, 5)
  - [ ] 3.1: Добавить обработку `mode=success` в метод `get()` класса `ICExchangeView`.
  - [ ] 3.2: В `handle_success`:
      - Использовать timestamp последнего `mode=query` (сохранённый в сессии пользователя в Task 2).
      - Обновить `sent_to_1c=True` только для заказов, где `sent_to_1c=False` И `created_at <= last_query_timestamp`.
      - Если timestamp в сессии нет (сессия истекла или прямой вызов), логировать warning и ничего не обновлять (или обновлять с осторожностью/возвращать ошибку).
      - **Цель:** Исключить Race Condition, когда новые заказы, пришедшие между query и success, помечаются как выгруженные.
  - [ ] 3.3: Вернуть "success".

- [ ] Task 4: Integration Tests (AC: 7, 8)
  - [ ] 4.1: Тест `test_mode_query_returns_xml`: Создать заказ, вызвать `checkauth`, затем `query`, проверить XML.
  - [ ] 4.2: Тест `test_mode_query_zip`: Передать `zip=yes`, проверить, что вернулся ZIP и внутри есть XML.
  - [ ] 4.3: Тест `test_mode_success_updates_status`: Вызвать `success`, проверить, что `sent_to_1c=True`.
  - [ ] 4.4: Тест `test_audit_logging`: Проверить, что файлы сохраняются в `media/1c_exchange/logs`.
  - [ ] 4.5: Использовать `APIClient` и фикстуры.

## Dev Notes

### Архитектурные требования

- **Толстые сервисы, тонкие взгляды:** `ICExchangeView` должен только оркестрировать процесс. Логика генерации XML — в `OrderExportService`.
- **Логирование:** Обязательно сохранять исходящие файлы. Это единственный способ отладки проблем с 1С на проде.

### Files to Touch

- `backend/apps/integrations/onec_exchange/views.py`: Основная реализация.
- `backend/tests/integration/test_onec_export.py`: Новые тесты (создать файл).

### Dependencies

- **OrderExportService**: Должен быть реализован в Story 4.2. Если 4.2 еще не готова, можно реализовать заглушку или объединить работы, но формально 4.3 зависит от 4.2.
- **Модель Order**: Поля `sent_to_1c` (Story 4.1).

### Anti-patterns

- ❌ Не писать генерацию XML внутри view.
- ❌ Не использовать `print` для отладки — только `logger`.
- ❌ Не забывать про `transaction.atomic` при массовом обновлении статусов.

### References

- [Source: backend/apps/integrations/onec_exchange/views.py] - Текущая реализация View.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3] - Оригинальные требования.
- [Source: backend/apps/orders/services/order_export.py] - Сервис экспорта (ожидается).

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

