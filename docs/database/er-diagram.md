# FREESPORT База Данных ER-Диаграмма

## Диаграмма Связей Сущностей

```mermaid
erDiagram
    %% Управление пользователями
    User {
        id bigint PK
        email varchar(254) UK "USERNAME_FIELD"
        first_name varchar(150)
        last_name varchar(150)
        password varchar(128)
        phone varchar(12) "формат +79001234567"
        is_active boolean
        date_joined timestamp
        role varchar(20) "retail, wholesale_level1, wholesale_level2, wholesale_level3, trainer, federation_rep, admin"
        company_name varchar(200) "для B2B пользователей"
        tax_id varchar(12) "ИНН для B2B"
        is_verified boolean "B2B верификация"
        is_staff boolean
        is_superuser boolean
        last_login timestamp
        created_at timestamp
        updated_at timestamp
    }

    Company {
        id bigint PK
        user_id bigint FK "OneToOne связь"
        legal_name varchar(255)
        tax_id varchar(12) UK
        kpp varchar(9)
        legal_address text
        bank_name varchar(200)
        bank_bik varchar(9)
        account_number varchar(20)
        created_at timestamp
        updated_at timestamp
    }

    Address {
        id bigint PK
        user_id bigint FK
        address_type varchar(10) "shipping, legal"
        full_name varchar(100)
        phone varchar(12)
        city varchar(100)
        street varchar(200)
        building varchar(10)
        apartment varchar(10)
        postal_code varchar(6)
        is_default boolean
        created_at timestamp
        updated_at timestamp
    }

    %% Управление товарами
    Brand {
        id bigint PK
        name varchar(100) UK
        slug varchar(100) UK
        logo varchar(255)
        description text
        website varchar(200)
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }

    Category {
        id bigint PK
        name varchar(200)
        slug varchar(200) UK
        parent_id bigint FK
        description text
        image varchar(255)
        is_active boolean
        sort_order integer
        seo_title varchar(200)
        seo_description text
        created_at timestamp
        updated_at timestamp
    }

    Product {
        id bigint PK
        name varchar(300)
        slug varchar(200) UK
        brand_id bigint FK
        category_id bigint FK
        description text
        short_description varchar(500)
        retail_price decimal "Розничная цена"
        opt1_price decimal "Оптовая цена уровень 1"
        opt2_price decimal "Оптовая цена уровень 2"
        opt3_price decimal "Оптовая цена уровень 3"
        trainer_price decimal "Цена для тренера"
        federation_price decimal "Цена для представителя федерации"
        recommended_retail_price decimal "Рекомендованная розничная цена (RRP)"
        max_suggested_retail_price decimal "Максимальная рекомендованная цена (MSRP)"
        sku varchar(100) UK
        stock_quantity integer
        min_order_quantity integer
        main_image varchar(255)
        gallery_images jsonb
        weight decimal
        dimensions jsonb
        specifications jsonb
        is_active boolean
        seo_title varchar(200)
        seo_description text
        created_at timestamp
        updated_at timestamp
    }

    %% Управление заказами
    Order {
        id bigint PK
        order_number varchar(50) UK
        user_id bigint FK "null для гостевых заказов"
        customer_name varchar(200) "для гостевых заказов"
        customer_email varchar(254) "для гостевых заказов"
        customer_phone varchar(20) "для гостевых заказов"
        status varchar(50) "pending, confirmed, processing, shipped, delivered, cancelled, refunded"
        total_amount decimal
        discount_amount decimal
        delivery_cost decimal
        delivery_address text
        delivery_method varchar(50)
        delivery_date date
        payment_method varchar(50)
        payment_status varchar(20)
        notes text
        created_at timestamp
        updated_at timestamp
    }

    OrderItem {
        id bigint PK
        order_id bigint FK
        product_id bigint FK
        quantity integer
        unit_price decimal "Цена по роли пользователя"
        total_price decimal
        product_name varchar(300) "Снимок данных на момент заказа"
        product_sku varchar(100) "Снимок данных на момент заказа"
        created_at timestamp
        updated_at timestamp
    }

    %% Управление корзиной
    Cart {
        id bigint PK
        user_id bigint FK "null для гостевых пользователей"
        session_key varchar(100) "для гостевых пользователей"
        created_at timestamp
        updated_at timestamp
    }

    CartItem {
        id bigint PK
        cart_id bigint FK
        product_id bigint FK
        quantity integer
        added_at timestamp
        updated_at timestamp
    }


    %% Аудиторский журнал
    AuditLog {
        id bigint PK
        user_id bigint FK
        action varchar(100)
        resource_type varchar(50)
        resource_id varchar(100)
        changes jsonb
        ip_address inet
        user_agent text
        timestamp timestamp
    }

    %% Журнал синхронизации с 1С
    SyncLog {
        id bigint PK
        sync_type varchar(50) "products, stocks, orders, prices"
        status varchar(20) "started, completed, failed"
        records_processed integer
        errors_count integer
        error_details jsonb
        started_at timestamp
        completed_at timestamp
    }

    %% Связи
    User ||--o| Company : "имеет компанию (OneToOne)"
    User ||--o{ Address : "имеет адреса (1:N)"
    
    Category ||--o{ Category : "имеет подкатегории"
    Brand ||--o{ Product : "производит товары"
    Category ||--o{ Product : "содержит товары"
    
    User ||--o| Cart : "имеет корзину"
    Cart ||--o{ CartItem : "содержит товары"
    Product ||--o{ CartItem : "в корзинах"
    
    User ||--o{ Order : "размещает заказы"
    Order ||--o{ OrderItem : "содержит товары"
    Product ||--o{ OrderItem : "заказанные товары"
    
    User ||--o{ AuditLog : "действия пользователя"
```

## Бизнес-Правила

### Роли пользователей и ценообразование
- **retail**: Розничный покупатель - retail_price
- **wholesale_level1**: Оптовик уровень 1 - opt1_price
- **wholesale_level2**: Оптовик уровень 2 - opt2_price  
- **wholesale_level3**: Оптовик уровень 3 - opt3_price
- **trainer**: Тренер - trainer_price
- **federation_rep**: Представитель федерации - federation_price
- **admin**: Администратор - полный доступ

### Информационные цены (только для отображения B2B пользователям)
- **recommended_retail_price**: Рекомендованная розничная цена (RRP)
- **max_suggested_retail_price**: Максимальная рекомендованная цена (MSRP)

### Статусы заказов
- **pending**: Ожидает обработки
- **confirmed**: Подтвержден
- **processing**: В обработке
- **shipped**: Отправлен
- **delivered**: Доставлен
- **cancelled**: Отменен
- **refunded**: Возвращен

### Типы адресов
- **shipping**: Адрес доставки
- **legal**: Юридический адрес

### Способы доставки
- **pickup**: Самовывоз
- **courier**: Курьерская доставка
- **post**: Почтовая доставка
- **transport**: Транспортная компания

### Типы синхронизации с 1С
- **products**: Товары
- **stocks**: Остатки
- **orders**: Заказы
- **prices**: Цены

### Статусы синхронизации
- **started**: Начата
- **completed**: Завершена
- **failed**: Ошибка

### Уникальные ограничения Cart и Orders
- Уникальная комбинация (cart, product) для CartItem - предотвращает дублирование товаров в корзине
- Уникальная комбинация (order, product) для OrderItem - предотвращает дублирование товаров в заказе, количество увеличивается в существующей позиции

## Ограничения и Валидации

### Ограничения на уровне базы данных
1. **Положительные значения**: Все цены, количества, суммы > 0
2. **Уникальные ограничения**: email, username, sku, order_number
3. **Ограничения внешних ключей**: Все связи должны существовать
4. **Check ограничения**: 
   - stock_quantity >= 0
   - total заказа = sum(order_items)
   - валидный формат email
   - валидный формат телефона

### Валидации бизнес-логики
1. **Управление складом**: quantity <= stock_quantity
2. **Правила ценообразования**: Правильная цена по роли пользователя
3. **Минимальные заказы**: quantity >= min_order_quantity
4. **Разрешения ролей**: Доступ к функциям по ролям
5. **Валидация компании**: B2B пользователи должны иметь company_id

## Соображения производительности

### Критические индексы
1. **Поиск товаров**: GIN индекс на название (полнотекстовый поиск)
2. **Фильтрация по категории**: (category_id, retail_price)
3. **Заказы пользователя**: (user_id, created_at DESC)
4. **Запросы по складу**: (sku, stock_quantity)
5. **Активные товары**: (is_active, category_id)

### Оптимизация запросов
- Используем select_related/prefetch_related для оптимизации JOIN
- Партицирование больших таблиц по дате
- Кеширование часто запрашиваемых данных
- Индексы для поддержки пользовательских ролей и ценообразования