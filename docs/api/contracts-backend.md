# Контракты Backend API

**(Обновлённый срез: 2026-05-02)**

## Базовый префикс

`/api/v1/`

## Каталог (`/products`, `/categories`, `/brands`)

- `GET /products/`: Список товаров с фильтрацией и пагинацией.
- `GET /products/{slug}/`: Детальная карточка товара.
- `GET /categories/`: Список категорий.
- `GET /categories-tree/`: Иерархическое дерево категорий.
- `GET /brands/`: Список брендов.
- `GET /catalog/filters/`: Динамические фильтры каталога.

## Корзина (`/cart`)

- `GET /cart/`: Текущая корзина пользователя или гостевой сессии.
- `DELETE /cart/clear/`: Очистка корзины.
- `POST /cart/items/`: Добавление позиции в корзину.
- `PATCH /cart/items/{id}/`: Изменение количества.
- `DELETE /cart/items/{id}/`: Удаление позиции.

## Заказы (`/orders`)

- `POST /orders/`: Создание заказа из корзины.
  - Требует авторизацию.
  - Требует валидный `customer_code` у пользователя.
  - Возвращает `OrderDetail` мастер-заказа.
- `GET /orders/`: Список только master-заказов текущего пользователя.
- `GET /orders/{id}/`: Детали master-заказа с агрегированными позициями sub-orders.
- `POST /orders/{id}/cancel/`: Отмена master-заказа с каскадной отменой sub-orders.

### Инварианты контракта заказов

- `order_number` в API всегда канонический:
  - master: `CCCCCYYNNN`
  - sub-order: `CCCCCYYNNNS`
- UI-формат (`CCCC-YYNNN` / `CCCCC-YYNNN-S`) не используется как API payload.
- Клиентские endpoint скрывают технические `sub-orders`; они используются для интеграции с 1С.

## Пользователи (`/users`, `/auth`)

- `POST /users/register/`: Регистрация пользователя.
- `POST /users/token/`: Получение JWT.
- `GET /users/me/`: Текущий профиль.
- `GET /users/company/`: B2B-профиль компании.

## Документация API

- Swagger UI: `/api/schema/swagger-ui/`
- ReDoc: `/api/schema/redoc/`
