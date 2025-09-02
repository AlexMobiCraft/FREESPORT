# 8. Основные Рабочие Процессы

### Процесс регистрации пользователя

```mermaid
flowchart TD
    A[Пользователь заполняет форму] --> B{Тип регистрации}
    B -->|B2C| C[Валидация email]
    B -->|B2B| D[Валидация компании + документы]
    
    C --> E[Отправка кода подтверждения]
    D --> F[Ручная модерация админом]
    
    E --> G[Пользователь вводит код]
    F --> H{Одобрено?}
    
    G --> I{Код верный?}
    H -->|Да| J[Активация B2B аккаунта]
    H -->|Нет| K[Отклонение с объяснением]
    
    I -->|Да| L[Активация B2C аккаунта]
    I -->|Нет| M[Повторная отправка кода]
    
    J --> N[Доступ к B2B ценам]
    L --> O[Доступ к розничным ценам]
    K --> P[Уведомление пользователю]
    M --> G
```

### Процесс создания заказа

```mermaid
sequenceDiagram
    participant User as Пользователь
    participant Frontend as Next.js Frontend
    participant BFF as Next.js API (BFF)
    participant Django as Django API
    participant YuKassa as ЮКасса
    participant Celery as Celery Worker
    participant OneC as 1C ERP

    User->>Frontend: Нажимает "Оформить заказ"
    Frontend->>BFF: POST /api/orders
    BFF->>Django: POST /orders/
    
    Django->>Django: Валидация корзины
    Django->>Django: Проверка остатков
    Django->>Django: Расчет цены по роли пользователя
    
    Django->>YuKassa: Создание платежа
    YuKassa-->>Django: Ссылка на оплату
    
    Django-->>BFF: Заказ + ссылка на оплату
    BFF-->>Frontend: Данные заказа
    Frontend-->>User: Редирект на оплату
    
    User->>YuKassa: Оплачивает заказ
    YuKassa->>Django: Webhook о статусе оплаты
    
    Django->>Celery: Задача экспорта в 1С
    Celery->>OneC: Экспорт заказа
    OneC-->>Celery: Подтверждение
    Celery->>Django: Обновление статуса
```

### Процесс синхронизации с 1С

```mermaid
flowchart TD
    A[Celery Beat Scheduler] --> B[Запуск задачи синхронизации]
    B --> C{Проверка Circuit Breaker}
    
    C -->|Open| D[HTTP запрос к 1С]
    C -->|Closed| E[Файловый экспорт]
    
    D --> F{1С доступна?}
    F -->|Да| G[Синхронизация товаров]
    F -->|Нет| H[Circuit Breaker -> Closed]
    
    G --> I[Обновление цен и остатков]
    I --> J[Экспорт новых заказов]
    J --> K[Импорт статусов заказов]
    
    E --> L[Создание XML файлов]
    L --> M[Сохранение в FTP папку]
    M --> N[Уведомление администратора]
    
    H --> O[Переход к файловому обмену]
    O --> L
    
    K --> P[Завершение синхронизации]
    N --> P
```

### Workflow управления ценами

```mermaid
stateDiagram-v2
    [*] --> PriceUpdate
    
    PriceUpdate --> B2CValidation: Розничная цена
    PriceUpdate --> B2BValidation: Оптовые цены
    
    B2CValidation --> PriceApproval: Валидация успешна
    B2BValidation --> PriceApproval: Валидация успешна
    
    PriceApproval --> AutoApproval: Изменение < 10%
    PriceApproval --> ManualApproval: Изменение > 10%
    
    AutoApproval --> PriceActivation
    ManualApproval --> AdminReview
    
    AdminReview --> PriceActivation: Одобрено
    AdminReview --> PriceRejection: Отклонено
    
    PriceActivation --> CacheInvalidation
    CacheInvalidation --> PriceNotification
    
    PriceNotification --> [*]
    PriceRejection --> [*]
```

### Процесс обработки возвратов

```mermaid
flowchart TD
    A[Клиент подает заявку на возврат] --> B[Создание Return Request]
    B --> C{Условия возврата?}
    
    C -->|В пределах 14 дней| D[Автоматическое одобрение]
    C -->|Вне срока| E[Ручное рассмотрение]
    C -->|Поврежденный товар| F[Запрос фотографий]
    
    D --> G[Генерация этикетки возврата]
    E --> H{Решение менеджера}
    F --> I[Рассмотрение фотографий]
    
    H -->|Одобрено| G
    H -->|Отклонено| J[Уведомление об отказе]
    I -->|Одобрено| G
    I -->|Отклонено| J
    
    G --> K[Получение товара на склад]
    K --> L[Проверка качества]
    L --> M{Товар в порядке?}
    
    M -->|Да| N[Возврат средств]
    M -->|Нет| O[Частичный возврат]
    
    N --> P[Обновление остатков в 1С]
    O --> P
    J --> Q[Закрытие заявки]
    P --> Q
```

---
