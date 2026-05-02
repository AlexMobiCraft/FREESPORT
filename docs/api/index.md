# Контракты API

См. [Контракты Backend API](./contracts-backend.md) для краткого обзора актуальных endpoint'ов, включая текущий contract `/orders/` с каноническим `order_number` и обязательным `customer_code` для checkout.

> **Актуализация от 2026-05-02:** `POST /api/orders/` требует аутентификации (`IsAuthenticated`). Анонимные запросы возвращают **401 Unauthorized**.

## Быстрые ссылки

- [Спецификация API (OpenAPI)](./openapi.yaml)
- [Документация по API Views](./views-documentation.md)
