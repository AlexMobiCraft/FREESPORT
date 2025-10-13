# Story 2.6: Cart API - Принятые технические решения

**Дата:** 17 августа 2025  
**Статус:** COMPLETED  
**Разработчик:** Claude Sonnet 4

## Context

- Корзина должна поддерживать как авторизованных пользователей с ролевыми ценами, так и гостей без учётных записей.
- Планировалась тесная интеграция с Catalog/Product APIs, поэтому требовались единые правила валидации и расчёта цен.
- Бизнес предъявил требования к скорейшему запуску MVP с возможностью бесшовной миграции гостевой корзины в пользовательскую.

## Decision

- Принята гибридная модель корзин (user_id + session_key), сервисы пересчёта позиций и валидации наличия/цен.
- Реализованы сервисы маппинга гостевых корзин, ролевое ценообразование и хендлеры синхронизации с заказами.
- Определены REST эндпоинты для CRUD операций, применение купонов, расчёта тоталов и очистки корзины.

## Consequences

- **Плюсы:** гибкость для B2B/B2C, консистентность с каталогом, готовность к интеграции с Order API.
- **Минусы:** усложнение логики хранения сессий и перерасчёта, повышенные требования к тестированию конкурирующих операций.
- **Технический долг:** переход на отдельный Cart Service, оптимизация хранения для больших корзин и внедрение rate limiting.

## Обзор

Документ описывает ключевые технические и архитектурные решения, принятые при реализации Story 2.6: Cart API с поддержкой гостевых корзин, валидацией товаров и ролевым ценообразованием.

## Архитектурные решения

### 1. Гибридная система корзин (авторизованные + гостевые)

**Решение:** Единая архитектура с поддержкой как user_id, так и session_key

**Структура Cart модели:**
```python
class Cart(models.Model):
    user = models.OneToOneField(User, null=True, blank=True)
    session_key = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [
            ('user',),  # Один пользователь = одна корзина
            ('session_key',)  # Одна сессия = одна корзина
        ]
```

**Логика определения корзины:**
```python
def get_or_create_cart(self, request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart
```

**Обоснование:**
- Единообразная работа для всех типов пользователей
- Возможность миграции гостевой корзины при авторизации
- Простота frontend интеграции (один API для всех случаев)
- Соответствие современным UX стандартам e-commerce

**Альтернативы рассмотренные:**
- Отдельные модели для гостевых корзин - отклонено из-за дублирования логики
- Только авторизованные корзины - отклонено из-за UX требований
- Хранение в cookies/localStorage - отклонено из-за ограничений размера

### 2. Автоматический перенос гостевой корзины

**Решение:** Django сигнал для автоматической миграции при авторизации

**Реализация сигнала:**
```python
@receiver(user_logged_in)
def merge_guest_cart_on_login(sender, request, user, **kwargs):
    session_key = request.session.session_key
    if not session_key:
        return
    
    try:
        guest_cart = Cart.objects.get(session_key=session_key)
        user_cart, created = Cart.objects.get_or_create(user=user)
        
        # Переносим товары из гостевой корзины
        for guest_item in guest_cart.items.all():
            user_item, created = CartItem.objects.get_or_create(
                cart=user_cart,
                product=guest_item.product,
                defaults={'quantity': guest_item.quantity}
            )
            if not created:
                # Объединяем количества если товар уже есть
                user_item.quantity += guest_item.quantity
                user_item.save()
        
        # Удаляем гостевую корзину
        guest_cart.delete()
        
    except Cart.DoesNotExist:
        pass
```

**Обоснование:**
- Seamless UX - пользователь не теряет товары при авторизации
- Автоматический процесс без вмешательства разработчика
- Правильное объединение товаров при конфликтах
- Очистка временных данных

### 3. Логика объединения одинаковых товаров (FR6.1)

**Решение:** Автоматическое объединение в CartItemCreateSerializer

**Реализация:**
```python
def create(self, validated_data):
    cart = validated_data['cart']
    product = validated_data['product']
    quantity = validated_data['quantity']
    
    # Проверяем существующий товар в корзине
    existing_item = CartItem.objects.filter(
        cart=cart, 
        product=product
    ).first()
    
    if existing_item:
        # Объединяем количества
        existing_item.quantity += quantity
        existing_item.save()
        return existing_item
    else:
        # Создаем новый элемент корзины
        return CartItem.objects.create(**validated_data)
```

**Обоснование:**
- Соответствие бизнес-требованию FR6.1
- Упрощение управления корзиной для пользователя
- Предотвращение дублирования товаров
- Стандартное поведение для e-commerce

### 4. Comprehensive валидация товаров

**Решение:** Многоуровневая валидация на уровне API и модели

**Валидации реализованы:**
1. **Существование товара:** проверка Product.objects.get()
2. **Активность товара:** product.is_active == True
3. **Наличие на складе:** product.stock_quantity >= requested_quantity
4. **Минимальное количество:** quantity >= product.min_order_quantity

**Код валидации:**
```python
def validate(self, data):
    product = data['product']
    quantity = data['quantity']
    
    if not product.is_active:
        raise ValidationError("Товар недоступен для заказа")
    
    if product.stock_quantity < quantity:
        raise ValidationError(
            f"Недостаточно товара на складе. Доступно: {product.stock_quantity}"
        )
    
    if quantity < product.min_order_quantity:
        raise ValidationError(
            f"Минимальное количество для заказа: {product.min_order_quantity}"
        )
    
    return data
```

**Обоснование:**
- Предотвращение overselling критически важно для бизнеса
- Раннее обнаружение проблем улучшает UX
- Соответствие B2B требованиям минимальных заказов
- API-level валидация защищает от некорректных данных

## Технические решения

### 1. ViewSet архитектура с явным роутингом

**Решение:** Использование отдельных ViewSets с custom URLs

**Структура endpoints:**
```python
# Cart ViewSet
GET    /api/v1/cart/           # Получение корзины
DELETE /api/v1/cart/clear/     # Очистка корзины

# CartItem ViewSet  
POST   /api/v1/cart/items/     # Добавление товара
PATCH  /api/v1/cart/items/{id}/ # Обновление количества
DELETE /api/v1/cart/items/{id}/ # Удаление товара
```

**Обоснование:**
- Избежание конфликтов URL patterns с другими apps
- Четкое разделение ответственности между ViewSets
- Стандартизация REST API patterns
- Простота frontend интеграции

**Альтернативы рассмотренные:**
- Nested routing через drf-nested-routers - отклонено из-за сложности
- Functional views - отклонено из-за отсутствия DRF features

### 2. Оптимизация запросов корзины

**Решение:** Comprehensive использование select_related и prefetch_related

**Оптимизированные запросы:**
```python
def get_queryset(self):
    return CartItem.objects.select_related(
        'product',
        'product__brand', 
        'product__category'
    ).prefetch_related(
        'product__gallery_images'
    )

def get_cart_data(self, cart):
    items = cart.items.select_related(
        'product', 'product__brand'
    ).all()
    
    # Один запрос для всех данных корзины
    return {
        'items': items,
        'total_items': sum(item.quantity for item in items),
        'total_amount': sum(item.total_price for item in items)
    }
```

**Обоснование:**
- Критическая важность производительности для корзины
- Избежание N+1 запросов при отображении товаров
- Масштабируемость для больших корзин
- Минимизация нагрузки на database

### 3. Ролевое ценообразование в корзине

**Решение:** Интеграция с Product.get_price_for_user() при отображении

**Реализация:**
```python
class CartItemDisplaySerializer(serializers.ModelSerializer):
    unit_price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    
    def get_unit_price(self, obj):
        request = self.context.get('request')
        user = request.user if request.user.is_authenticated else None
        return obj.product.get_price_for_user(user)
    
    def get_total_price(self, obj):
        unit_price = self.get_unit_price(obj)
        return unit_price * obj.quantity
```

**Обоснование:**
- Единообразие с каталогом и системой ценообразования
- Автоматическое обновление цен при изменении роли
- Прозрачность для пользователя
- Подготовка к созданию заказов с правильными ценами

### 4. Management команды для обслуживания

**Решение:** Cleanup команда для старых гостевых корзин

**Реализация:**
```python
# management/commands/cleanup_guest_carts.py
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)
    
    def handle(self, *args, **options):
        cutoff_date = timezone.now() - timedelta(days=options['days'])
        
        deleted_count = Cart.objects.filter(
            user__isnull=True,  # Только гостевые корзины
            updated_at__lt=cutoff_date
        ).delete()[0]
        
        self.stdout.write(f"Удалено {deleted_count} старых гостевых корзин")
```

**Обоснование:**
- Предотвращение накопления неиспользуемых данных
- Регулярная очистка database от временных сессий
- Соответствие GDPR требованиям
- Production-ready обслуживание

## Решения по интеграции

### 1. Интеграция с Product API

**Решение:** Полное переиспользование логики товаров

**Интегрированные features:**
- Ролевое ценообразование через get_price_for_user()
- Валидация остатков через stock_quantity
- Обработка изображений через main_image
- B2B правила через min_order_quantity

**Преимущества:**
- Единая точка истины для данных товаров
- Автоматическая синхронизация с изменениями каталога
- Переиспользование существующих валидаций

### 2. Подготовка к Order API

**Решение:** Структурирование корзины для легкого создания заказов

**Подготовленные данные:**
```python
{
    "items": [
        {
            "product": {...},
            "quantity": 2,
            "unit_price": "2500.00",  # Актуальная цена по роли
            "total_price": "5000.00"
        }
    ],
    "total_amount": "5500.00",  # С учетом доставки
    "total_items": 2
}
```

**Обоснование:**
- Простота миграции данных в Order/OrderItem
- Сохранение актуальных цен на момент заказа
- Готовность к транзакционному созданию заказов

### 3. Session Management

**Решение:** Автоматическое создание сессий для анонимных пользователей

**Реализация:**
```python
def ensure_session(self, request):
    if not request.session.session_key:
        request.session.create()
        request.session.save()
    return request.session.session_key
```

**Обоснование:**
- Гарантированная работа гостевых корзин
- Правильное управление Django сессиями
- Подготовка к аналитике поведения пользователей

## Решения по тестированию

### 1. Комплексное API тестирование

**Покрытие тестами:**
- Получение пустой корзины (авторизованные/гости)
- Добавление товаров с объединением одинаковых
- Валидация остатков и минимальных количеств
- Обновление и удаление товаров
- Очистка корзины
- Перенос гостевой корзины при авторизации

**Тестовые сценарии:**
```python
def test_guest_cart_merge_on_login():
    # Создаем гостевую корзину
    guest_client = APIClient()
    guest_client.post('/api/v1/cart/items/', data)
    
    # Авторизуемся
    guest_client.post('/api/v1/auth/login/', login_data)
    
    # Проверяем, что товары перенеслись
    response = guest_client.get('/api/v1/cart/')
    assert response.data['total_items'] > 0
```

### 2. Mock-based unit тесты

**Изоляция зависимостей:**
```python
@patch('apps.products.models.Product.get_price_for_user')
def test_cart_item_total_price_calculation(self, mock_get_price):
    mock_get_price.return_value = Decimal('2500.00')
    
    item = CartItem.objects.create(
        cart=self.cart,
        product=self.product, 
        quantity=2
    )
    
    serializer = CartItemDisplaySerializer(item, context={'request': self.request})
    assert serializer.data['total_price'] == '5000.00'
```

**Обоснование:**
- Изоляция тестов от внешних зависимостей
- Контролируемое тестирование граничных случаев
- Быстрое выполнение unit тестов

### 3. Integration тестирование

**End-to-end сценарии:**
- Полный flow: добавление → обновление → удаление
- Работа с реальными изображениями товаров
- Интеграция с системой аутентификации
- Валидация с реальными данными товаров

## Производственные соображения

### 1. Производительность

**Оптимизации:**
- Минимизация SQL запросов через select_related
- Эффективные индексы на cart_id и product_id
- Bulk операции для массовых изменений корзины

**Мониторинг производительности:**
- Время отклика cart API
- Количество SQL запросов на операцию
- Memory usage при больших корзинах

### 2. Масштабируемость

**Архитектурные решения:**
- Stateless API для горизонтального масштабирования
- Возможность вынесения корзин в отдельную database
- Redis кэширование для активных корзин (планируется)

### 3. Безопасность корзин

**Меры безопасности:**
- Автоматическая фильтрация по пользователю/сессии
- Валидация всех входных данных
- Защита от переполнения корзины
- Rate limiting для cart operations (планируется)

## Пользовательский опыт

### 1. Seamless Experience

**UX Features:**
- Сохранение корзины между сессиями
- Автоматический перенос при авторизации
- Мгновенное обновление количества товаров
- Валидация с понятными сообщениями об ошибках

### 2. Персонализация корзины

**Ролевые различия:**
- B2B: минимальные количества, оптовые цены
- B2C: розничные цены, рекомендации
- Анонимные: базовые цены, призыв к регистрации

### 3. Подготовка к покупке

**Pre-checkout features:**
- Актуальные цены и наличие
- Расчет предварительной стоимости
- Валидация перед переходом к оформлению

## Будущие улучшения

### Краткосрочные (следующие 2-4 недели)
1. Интеграция с Order API для создания заказов
2. Расчет предварительной стоимости доставки
3. Сохранение товаров "на потом"

### Среднесрочные (1-3 месяца)
1. Рекомендации в корзине ("Часто покупают вместе")
2. Bulk операции (добавление нескольких товаров)
3. Уведомления об изменении цен в корзине

### Долгосрочные (3-6 месяцев)
1. Wishlist интеграция
2. Sharing корзины между пользователями (B2B)
3. Abandoned cart recovery через email

## Заключение

Story 2.6 создала полнофункциональную систему корзин для FREESPORT:

✅ **Гибридная архитектура** - поддержка авторизованных и гостевых пользователей  
✅ **Seamless UX** - автоматический перенос корзин, объединение товаров  
✅ **Comprehensive валидация** - остатки, минимальные количества, активность товаров  
✅ **Ролевое ценообразование** - интеграция с системой ценообразования  
✅ **Production готовность** - оптимизация, мониторинг, обслуживание  

Cart API обеспечивает все необходимые функции для управления корзиной и готов к интеграции с системой заказов для завершения покупательского процесса.