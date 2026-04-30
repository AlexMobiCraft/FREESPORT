---
name: production-database
description: Используй этот навык для выполнения SQL-запросов к базе данных PostgreSQL на продакшен-сервере FREESPORT. Включает команды для проверки сессий импорта 1С, товаров, заказов и других таблиц.
---

# Production Database Skill

Навык для работы с PostgreSQL базой данных на продакшен-сервере.

## Параметры подключения

- **Host:** `5.35.124.149`
- **SSH User:** `root`
- **SSH Аутентификация:** SSH ключ (без пароля)
- **Database:** `freesport`
- **DB User:** `postgres`
- **Project Path:** `/home/freesport/freesport/`

## Базовая команда для SQL-запросов

Шаблон команды через SSH + Docker:

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -c "SQL_QUERY_HERE"'
```

> [!IMPORTANT]
> - Всегда делайте `cd /home/freesport/freesport &&` перед `docker compose` — команда ищет `.env.prod` относительно текущей директории.
> - Используйте абсолютный путь `--env-file /home/freesport/freesport/.env.prod` для надёжности.

## Флаги psql

- `-t` — только данные (без заголовков и рамок)
- `-c "QUERY"` — выполнить SQL-запрос
- `-A` — unaligned output (без выравнивания)
- `-f /tmp/query.sql` — выполнить SQL из файла (используйте с here-document для сложных запросов)

## Основные таблицы проекта

### 🛒 Products (Товары)

| Таблица                       | Описание                        |
| ----------------------------- | ------------------------------- |
| `products`                    | Товары                          |
| `product_variants`            | Варианты товаров (SKU)          |
| `product_variants_attributes` | Связь вариантов с атрибутами    |
| `product_attributes`          | Атрибуты товаров (размер, цвет) |
| `product_attribute_values`    | Значения атрибутов              |
| `product_images`              | Изображения товаров             |
| `products_attributes`         | Связь товаров с атрибутами      |
| `categories`                  | Категории товаров               |
| `brands`                      | Бренды                          |
| `price_types`                 | Типы цен (розница, опт)         |
| `favorites`                   | Избранные товары                |

### 📦 Orders (Заказы)

| Таблица                   | Описание         |
| ------------------------- | ---------------- |
| `orders`                  | Заказы           |
| `order_items`             | Позиции заказов  |
| `delivery_deliverymethod` | Способы доставки |

### 🛍️ Cart (Корзина)

| Таблица      | Описание              |
| ------------ | --------------------- |
| `carts`      | Корзины пользователей |
| `cart_items` | Товары в корзине      |

### 👤 Users (Пользователи)

| Таблица                  | Описание                       |
| ------------------------ | ------------------------------ |
| `users`                  | Пользователи                   |
| `users_groups`           | Связь пользователей с группами |
| `users_user_permissions` | Права пользователей            |
| `addresses`              | Адреса доставки                |
| `companies`              | Компании (B2B)                 |

### 📰 Common (Контент и логи)

| Таблица                        | Описание                   |
| ------------------------------ | -------------------------- |
| `common_news`                  | Новости                    |
| `common_blogpost`              | Блог-посты                 |
| `common_category`              | Категории контента         |
| `common_newsletter`            | Подписки на рассылку       |
| `common_notificationrecipient` | Получатели уведомлений     |
| `common_auditlog`              | Лог аудита                 |
| `common_synclog`               | Лог синхронизации          |
| `common_syncconflict`          | Конфликты синхронизации    |
| `common_customersynclog`       | Лог синхронизации клиентов |

### 🏷️ Banners

| Таблица   | Описание            |
| --------- | ------------------- |
| `banners` | Баннеры Hero-секции |

### 📄 Pages

| Таблица      | Описание             |
| ------------ | -------------------- |
| `pages_page` | Статические страницы |

### 🔄 1C Import (Интеграция с 1С)

| Таблица                               | Описание                      |
| ------------------------------------- | ----------------------------- |
| `import_sessions`                     | Сессии импорта из 1С          |
| `products_brand_1c_mapping`           | Маппинг брендов 1С            |
| `product_attribute_1c_mappings`       | Маппинг атрибутов 1С          |
| `product_attribute_value_1c_mappings` | Маппинг значений атрибутов 1С |
| `color_mappings`                      | Маппинг цветов                |

### 🔐 Auth & Django

| Таблица                            | Описание             |
| ---------------------------------- | -------------------- |
| `auth_group`                       | Группы пользователей |
| `auth_group_permissions`           | Права групп          |
| `auth_permission`                  | Разрешения           |
| `django_admin_log`                 | Лог админки          |
| `django_content_type`              | Типы контента        |
| `django_migrations`                | Миграции             |
| `django_session`                   | Сессии Django        |
| `token_blacklist_blacklistedtoken` | Чёрный список JWT    |
| `token_blacklist_outstandingtoken` | Активные JWT токены  |

## Экранирование и сложные SQL-запросы

### Проблема с одинарными кавычками в SQL

Если SQL-запрос содержит одинарные кавычки (например, `WHERE name = 'test'`), они конфликтуют с одинарными кавычками `'...'` вокруг SSH-команды.

**Решения:**

1. **Двойные кавычки вокруг SQL** (внутри одинарных кавычек PowerShell):

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -c "SELECT * FROM products WHERE name = ''test''"'
```

2. **Here-document для сложных запросов** (рекомендуется):

```powershell
ssh root@5.35.124.149 'cat > /tmp/query.sql << "EOF"
SELECT * FROM products WHERE name = ''test'' AND status = ''active'';
EOF
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -f /tmp/query.sql'
```

3. **chr(37) вместо `%` для LIKE** (PowerShell интерпретирует `%`):

```sql
-- Вместо: LIKE '%import%'
-- Используйте: LIKE chr(37)||'import'||chr(37)
```

4. **Удаление временного файла после выполнения:**

```powershell
ssh root@5.35.124.149 'rm /tmp/query.sql'
```

### Логи без обрезки

Для полных логов без обрезки длинных строк:

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml logs --tail=50 --no-trunc backend 2>&1 | cat'
```

## Готовые SQL-запросы

### Проверка сессий импорта 1С (последние 10)

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -t -c "SELECT id, status, created_at FROM import_sessions ORDER BY created_at DESC LIMIT 10;"'
```

### Подсчёт товаров

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -t -c "SELECT COUNT(*) FROM products_product;"'
```

### Подсчёт вариантов товаров

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -t -c "SELECT COUNT(*) FROM products_productvariant;"'
```

### Последние 5 заказов

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -t -c "SELECT id, status, total, created_at FROM orders_order ORDER BY created_at DESC LIMIT 5;"'
```

### Список всех таблиц

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -c "\dt"'
```

### Структура таблицы

Замените `TABLE_NAME` на имя таблицы:

```powershell
ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T db psql -U postgres -d freesport -c "\d TABLE_NAME"'
```

## Советы по работе с PowerShell

> [!WARNING]
> PowerShell интерпретирует специальные символы (`$`, `%`, кавычки). **Всегда используйте одинарные кавычки `'...'`** на уровне PowerShell — bash получает строку как есть.

### Избегайте в SQL:

- Одинарных кавычек `'...'` вокруг всей SSH-команды, если SQL содержит одинарные кавычки — используйте here-document (см. раздел выше)
- Символ `%` для LIKE — при необходимости используйте функцию `chr(37)`:
  ```sql
  -- Вместо: LIKE '%import%'
  -- Используйте: LIKE chr(37)||'import'||chr(37)
  ```

### Разделитель команд

- В PowerShell используйте `;` для разделения команд PowerShell.
- Внутри SSH-строки (одинарные кавычки) используйте `&&` или `;` для bash.
- Всегда объединяйте `cd` и `docker compose` через `&&` внутри SSH-строки:
  ```powershell
  ssh root@5.35.124.149 'cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod ...'
  ```

## Альтернатива: Django ORM через shell

Для сложных запросов можно использовать Django shell. **Важно:** интерактивный shell через SSH сложен в автоматизации. Для скриптов используйте here-document:

```powershell
ssh root@5.35.124.149 'cat > /tmp/django_script.py << "EOF"
from apps.products.models import Product
print(Product.objects.count())
EOF
cd /home/freesport/freesport && docker compose --env-file /home/freesport/freesport/.env.prod -f docker/docker-compose.prod.yml exec -T backend python manage.py shell < /tmp/django_script.py'
```

> [!CAUTION]
> Будьте крайне осторожны с UPDATE/DELETE запросами на продакшен базе. Всегда делайте backup перед изменениями.
