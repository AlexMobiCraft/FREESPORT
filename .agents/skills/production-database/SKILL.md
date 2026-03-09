---
name: production-database
description: Используй этот навык для выполнения SQL-запросов к базе данных PostgreSQL на продакшен-сервере FREESPORT. Включает команды для проверки сессий импорта 1С, товаров, заказов и других таблиц.
---

# Production Database Skill

Навык для работы с PostgreSQL базой данных на продакшен-сервере.

## Параметры подключения

*   **Host:** `5.35.124.149`
*   **SSH User:** `root`
*   **SSH Key Passphrase:** `0301`
*   **Database:** `freesport`
*   **DB User:** `postgres`
*   **Project Path:** `/home/freesport/freesport/`

## Базовая команда для SQL-запросов

Шаблон команды через SSH + Docker:

```powershell
ssh root@5.35.124.149 "cd /home/freesport/freesport/ && docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -c 'SQL_QUERY_HERE'"
```

> [!IMPORTANT]
> После запуска SSH-команды нужно ввести passphrase `0301` для ключа.

## Флаги psql

- `-t` — только данные (без заголовков и рамок)
- `-c 'QUERY'` — выполнить SQL-запрос
- `-A` — unaligned output (без выравнивания)

## Основные таблицы проекта

### 🛒 Products (Товары)

| Таблица | Описание |
|---------|----------|
| `products` | Товары |
| `product_variants` | Варианты товаров (SKU) |
| `product_variants_attributes` | Связь вариантов с атрибутами |
| `product_attributes` | Атрибуты товаров (размер, цвет) |
| `product_attribute_values` | Значения атрибутов |
| `product_images` | Изображения товаров |
| `products_attributes` | Связь товаров с атрибутами |
| `categories` | Категории товаров |
| `brands` | Бренды |
| `price_types` | Типы цен (розница, опт) |
| `favorites` | Избранные товары |

### 📦 Orders (Заказы)

| Таблица | Описание |
|---------|----------|
| `orders` | Заказы |
| `order_items` | Позиции заказов |
| `delivery_deliverymethod` | Способы доставки |

### 🛍️ Cart (Корзина)

| Таблица | Описание |
|---------|----------|
| `carts` | Корзины пользователей |
| `cart_items` | Товары в корзине |

### 👤 Users (Пользователи)

| Таблица | Описание |
|---------|----------|
| `users` | Пользователи |
| `users_groups` | Связь пользователей с группами |
| `users_user_permissions` | Права пользователей |
| `addresses` | Адреса доставки |
| `companies` | Компании (B2B) |

### 📰 Common (Контент и логи)

| Таблица | Описание |
|---------|----------|
| `common_news` | Новости |
| `common_blogpost` | Блог-посты |
| `common_category` | Категории контента |
| `common_newsletter` | Подписки на рассылку |
| `common_notificationrecipient` | Получатели уведомлений |
| `common_auditlog` | Лог аудита |
| `common_synclog` | Лог синхронизации |
| `common_syncconflict` | Конфликты синхронизации |
| `common_customersynclog` | Лог синхронизации клиентов |

### 🏷️ Banners

| Таблица | Описание |
|---------|----------|
| `banners` | Баннеры Hero-секции |

### 📄 Pages

| Таблица | Описание |
|---------|----------|
| `pages_page` | Статические страницы |

### 🔄 1C Import (Интеграция с 1С)

| Таблица | Описание |
|---------|----------|
| `import_sessions` | Сессии импорта из 1С |
| `products_brand_1c_mapping` | Маппинг брендов 1С |
| `product_attribute_1c_mappings` | Маппинг атрибутов 1С |
| `product_attribute_value_1c_mappings` | Маппинг значений атрибутов 1С |
| `color_mappings` | Маппинг цветов |

### 🔐 Auth & Django

| Таблица | Описание |
|---------|----------|
| `auth_group` | Группы пользователей |
| `auth_group_permissions` | Права групп |
| `auth_permission` | Разрешения |
| `django_admin_log` | Лог админки |
| `django_content_type` | Типы контента |
| `django_migrations` | Миграции |
| `django_session` | Сессии Django |
| `token_blacklist_blacklistedtoken` | Чёрный список JWT |
| `token_blacklist_outstandingtoken` | Активные JWT токены |

## Готовые SQL-запросы

### Проверка сессий импорта 1С (последние 10)

```powershell
ssh root@5.35.124.149 "cd /home/freesport/freesport/ && docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -t -c 'SELECT id, status, created_at FROM import_sessions ORDER BY created_at DESC LIMIT 10;'"
```

### Подсчёт товаров

```powershell
ssh root@5.35.124.149 "cd /home/freesport/freesport/ && docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -t -c 'SELECT COUNT(*) FROM products_product;'"
```

### Подсчёт вариантов товаров

```powershell
ssh root@5.35.124.149 "cd /home/freesport/freesport/ && docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -t -c 'SELECT COUNT(*) FROM products_productvariant;'"
```

### Последние 5 заказов

```powershell
ssh root@5.35.124.149 "cd /home/freesport/freesport/ && docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -t -c 'SELECT id, status, total, created_at FROM orders_order ORDER BY created_at DESC LIMIT 5;'"
```

### Список всех таблиц

```powershell
ssh root@5.35.124.149 "cd /home/freesport/freesport/ && docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -c '\dt'"
```

### Структура таблицы

Замените `TABLE_NAME` на имя таблицы:

```powershell
ssh root@5.35.124.149 "cd /home/freesport/freesport/ && docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -c '\d TABLE_NAME'"
```

## Советы по работе с PowerShell

> [!WARNING]
> PowerShell интерпретирует специальные символы (`$`, `%`, кавычки). Используйте **одинарные кавычки** для SQL-запросов внутри SSH-команды.

### Избегайте в SQL:
- Двойных кавычек `"` — заменяйте на escape или используйте только одинарные
- Символ `%` для LIKE — при необходимости используйте функцию `chr(37)`:
  ```sql
  -- Вместо: LIKE '%import%'
  -- Используйте: LIKE chr(37)||'import'||chr(37)
  ```

## Альтернатива: Django ORM через shell

Для сложных запросов можно использовать Django shell:

```powershell
ssh root@5.35.124.149 "cd /home/freesport/freesport/ && docker compose --env-file .env.prod -f docker/docker-compose.prod.yml exec -T backend python manage.py shell"
```

Затем вводить Python-код интерактивно.

> [!CAUTION]
> Будьте крайне осторожны с UPDATE/DELETE запросами на продакшен базе. Всегда делайте backup перед изменениями.
