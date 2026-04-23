# Acceptance Auditor Prompt

Роль: reviewer, который проверяет реализацию против спецификации и контекстных docs.

Вход:

- файл `review-diff-1c-order-price-includes-vat.md`
- файл `spec-1c-order-price-includes-vat.md`
- read-only доступ к репозиторию FREESPORT

Перед проверкой обязательно прочитай:

- `spec-1c-order-price-includes-vat.md`
- `..\..\docs\integrations\1c\order-vat-warehouse-routing.md`
- `..\..\docs\integrations\1c\order-import-handler-diagnostics.md`

Ограничения:

- не использовать контекст этой переписки;
- проверять только соответствие intent, boundaries, acceptance criteria и контекстным правилам;
- отдельно отмечать, если изменение уводит проблему в настройку 1С без исправления XML-контракта.

Проверь:

1. Исправлен ли именно XML-контракт тега включения НДС в сумму.
2. Сохранена ли текущая математика брутто-цены и суммы НДС.
3. Покрыт ли регрессией риск возвращения старого имени тега.
4. Согласованы ли docs/sample с кодом.
5. Нет ли отклонений от `Always`, `Ask First`, `Never` и acceptance criteria из spec.

Формат ответа:

- findings first;
- для каждой находки: category suggestion (`bad_spec` или `patch`), severity, file/line, violated acceptance/constraint;
- если находок нет, явно напиши `Находок нет`.
