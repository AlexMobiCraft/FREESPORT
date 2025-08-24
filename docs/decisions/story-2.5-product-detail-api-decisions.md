# Story 2.5: Product Detail API - Принятые технические решения

**Дата:** 17 августа 2025  
**Статус:** COMPLETED  
**Разработчик:** Claude Sonnet 4

## Обзор

Документ описывает ключевые технические и архитектурные решения, принятые при реализации Story 2.5: Product Detail API с расширенными данными, ролевым ценообразованием и галереей изображений.

## Архитектурные решения

### 1. Расширение Product модели спецификациями

**Решение:** Добавление JSON поля specifications в Product модель

**Миграция:**
```python
# 0005_product_specifications.py
operations = [
    migrations.AddField(
        model_name='product',
        name='specifications',
        field=models.JSONField(blank=True, default=dict, verbose_name='Технические характеристики'),
    ),
]
```

**Структура спецификаций:**
```json
{
    "material": "100% полиэстер",
    "size_range": "XS-XXL", 
    "weight": "150г",
    "color_options": ["Черный", "Белый", "Синий"],
    "care_instructions": "Машинная стирка 30°C",
    "country_of_origin": "Вьетнам"
}
```

**Обоснование:**
- Гибкость для различных типов спортивных товаров
- PostgreSQL JSONB обеспечивает производительность и индексацию
- Простота добавления новых характеристик без миграций
- Подготовка к фасетному поиску по характеристикам

**Альтернативы рассмотренные:**
- Отдельные модели для каждого типа характеристик - отклонено из-за сложности
- EAV (Entity-Attribute-Value) модель - отклонено из-за производительности

### 2. Структурированная галерея изображений

**Решение:** ProductImageSerializer для унификации обработки изображений

**Архитектура:**
```python
class ProductImageSerializer(serializers.Serializer):
    url = serializers.SerializerMethodField()
    alt_text = serializers.SerializerMethodField() 
    is_primary = serializers.SerializerMethodField()
    
    def get_alt_text(self, image_data):
        if image_data.get('is_main'):
            return f"{self.instance.name} - основное изображение"
        return f"{self.instance.name} - дополнительное изображение"
```

**Структура gallery_images JSON:**
```json
[
    {
        "url": "/media/products/nike-shirt-1.jpg",
        "alt_text": "Nike футболка - вид спереди",
        "is_primary": false
    },
    {
        "url": "/media/products/nike-shirt-2.jpg", 
        "alt_text": "Nike футболка - вид сзади",
        "is_primary": false
    }
]
```

**Обоснование:**
- SEO оптимизация через правильные alt тексты
- Структурированные данные для frontend отображения
- Готовность к responsive images с разными размерами
- Простота добавления метаданных (размер, цвет, ракурс)

### 3. Расширенное ролевое ценообразование

**Решение:** Полная информация о ценах с расчетом скидок для каждой роли

**Ценовая структура:**
```python
def get_price_info(self, obj):
    request = self.context.get('request')
    user = request.user if request and request.user.is_authenticated else None
    
    price_info = {
        'current_price': self.format_decimal(obj.get_price_for_user(user)),
        'retail_price': self.format_decimal(obj.retail_price),
    }
    
    # B2B информационные цены
    if user and user.role in self.B2B_ROLES:
        price_info.update({
            'recommended_retail_price': self.format_decimal(obj.recommended_retail_price),
            'max_suggested_retail_price': self.format_decimal(obj.max_suggested_retail_price),
        })
    
    # Расчет скидки от retail_price
    if obj.retail_price and obj.get_price_for_user(user) < obj.retail_price:
        discount = ((obj.retail_price - obj.get_price_for_user(user)) / obj.retail_price) * 100
        price_info['discount_percent'] = round(discount, 1)
    
    return price_info
```

**Обоснование:**
- Прозрачность ценообразования для B2B клиентов
- Мотивация к покупке через отображение скидки
- Единообразие с каталогом, но с расширенной информацией
- Подготовка к системе динамических скидок

### 4. Связанные товары (Related Products)

**Решение:** Автоматический подбор по категории и бренду с исключением текущего товара

**Алгоритм подбора:**
```python
def get_related_products(self, obj):
    related_products = Product.objects.filter(
        category=obj.category,
        brand=obj.brand,
        is_active=True
    ).exclude(
        id=obj.id
    ).select_related(
        'brand', 'category'
    )[:5]
    
    # Применяем ролевое ценообразование к связанным товарам
    return ProductListSerializer(
        related_products, 
        many=True, 
        context=self.context
    ).data
```

**Обоснование:**
- Увеличение среднего чека через cross-selling
- Релевантность через категорию и бренд
- Ограничение 5 товаров предотвращает перегрузку UI
- Ролевое ценообразование сохраняется для связанных товаров

**Планируемые улучшения:**
- ML-алгоритмы для персонализированных рекомендаций
- A/B тестирование алгоритмов подбора
- Интеграция с историей покупок

## Технические решения

### 1. Унифицированный формат цен

**Решение:** Стандартизация всех цен с 2 десятичными знаками

**Реализация:**
```python
def format_decimal(self, value):
    if value is None:
        return None
    return f"{value:.2f}"
```

**Обоснование:**
- Консистентность отображения цен во всем API
- Предотвращение проблем с floating point арифметикой
- Готовность к международным валютам
- Стандартизация для финансовых расчетов

### 2. Computed Properties интеграция

**Решение:** Использование существующих computed properties из Product модели

**Интегрированные properties:**
- `is_in_stock` - наличие на складе (stock_quantity > 0)
- `can_be_ordered` - возможность заказа (учитывает is_active + is_in_stock)

**Обоснование:**
- Повторное использование бизнес-логики из модели
- Единообразие логики во всей системе
- Упрощение поддержки при изменении правил

### 3. SEO оптимизация

**Решение:** Включение SEO метаданных в API ответ

**SEO поля:**
```python
{
    "seo_title": "Nike Dri-FIT футболка для тренировок",
    "seo_description": "Профессиональная футболка Nike с технологией Dri-FIT для интенсивных тренировок. Быстрое отведение влаги, комфортная посадка.",
    "meta_keywords": ["nike", "футболка", "dri-fit", "тренировки"]
}
```

**Обоснование:**
- SSR поддержка для SEO оптимизации
- Централизованное управление meta тегами
- Готовность к автоматической генерации описаний

### 4. Обработка отсутствующих данных

**Решение:** Graceful degradation для опциональных полей

**Стратегии обработки:**
```python
def get_gallery_images(self, obj):
    if not obj.gallery_images:
        return []
    return self.process_gallery_images(obj.gallery_images)

def get_specifications(self, obj):
    return obj.specifications or {}

def get_related_products(self, obj):
    # Возвращаем пустой список если нет связанных товаров
    return related_data or []
```

**Обоснование:**
- Устойчивость к неполным данным
- Улучшенный UX через отсутствие ошибок
- Готовность к миграции существующих товаров

## Решения по интеграции

### 1. Навигационная цепочка (Breadcrumbs)

**Решение:** Интеграция с Category модели для полной навигации

**Реализация:**
```python
def get_category_info(self, obj):
    if not obj.category:
        return None
    
    return {
        'id': obj.category.id,
        'name': obj.category.name,
        'slug': obj.category.slug,
        'breadcrumbs': obj.category.breadcrumbs  # Computed property
    }
```

**Обоснование:**
- Улучшенная навигация для пользователей
- SEO преимущества через структурированную навигацию
- Интеграция с существующей логикой категорий

### 2. Brand информация

**Решение:** Расширенная информация о бренде товара

**Структура brand_info:**
```python
{
    "id": 1,
    "name": "Nike",
    "slug": "nike", 
    "logo": "/media/brands/nike.png",
    "website": "https://nike.com"
}
```

**Обоснование:**
- Возможность перехода на страницу бренда
- Брендинг и доверие покупателей
- Подготовка к брендовым промо-страницам

### 3. Интеграция с Favorites API

**Решение:** Подготовка к отображению статуса "в избранном"

**Планируемая интеграция:**
```python
def get_is_favorite(self, obj):
    request = self.context.get('request')
    if request and request.user.is_authenticated:
        return Favorite.objects.filter(
            user=request.user, 
            product=obj
        ).exists()
    return False
```

**Обоснование:**
- Улучшенный UX через показ статуса избранного
- Быстрое добавление/удаление из избранного
- Персонализация страницы товара

## Решения по тестированию

### 1. Comprehensive функциональное тестирование

**Тестовые сценарии:**
```python
def test_product_detail_complete():
    # Тест всех полей в ответе
    response = self.client.get(f'/api/v1/products/{self.product.id}/')
    
    assert 'specifications' in response.data
    assert 'gallery_images' in response.data
    assert 'related_products' in response.data
    assert 'current_price' in response.data
    assert 'category_info' in response.data
```

### 2. Ролевое ценообразование

**Покрытие всех ролей:**
```python
def test_role_based_pricing_detail():
    roles_prices = [
        ('retail', '3000.00'),
        ('wholesale_level1', '2800.00'),
        ('wholesale_level2', '2500.00'),
        ('trainer', '2200.00'),
    ]
    
    for role, expected_price in roles_prices:
        user = create_user(role=role)
        response = get_product_detail(user, self.product.id)
        assert response.data['current_price'] == expected_price
```

### 3. Граничные случаи

**Edge cases тестирование:**
- Товар без изображений
- Товар без спецификаций  
- Товар без связанных товаров
- Неактивный товар (404 response)
- Товар с некорректными ценами

## Производственные соображения

### 1. Кэширование

**Стратегия кэширования:**
- Полная страница товара для анонимных пользователей
- Персонализированное кэширование по ролям
- Cache invalidation при изменении товара

**Реализация (планируемая):**
```python
@method_decorator(cache_page(60 * 15))  # 15 минут для анонимных
def retrieve(self, request, *args, **kwargs):
    if not request.user.is_authenticated:
        return super().retrieve(request, *args, **kwargs)
    # Персонализированная логика для авторизованных
```

### 2. Производительность изображений

**Оптимизации:**
- Lazy loading для gallery_images
- Различные размеры изображений (thumbnail, medium, large)
- CDN интеграция для быстрой загрузки
- WebP формат для современных браузеров

### 3. Мониторинг товаров

**Ключевые метрики:**
- Время загрузки страницы товара
- Конверсия с детальной страницы в корзину
- Популярность связанных товаров
- Bounce rate на страницах товаров

## Пользовательский опыт

### 1. Rich Product Information

**Информационная полнота:**
- Детальные технические характеристики
- Множественные изображения с разных ракурсов
- Полная ценовая информация по роли
- Навигационный контекст через breadcrumbs

### 2. Персонализация

**Ролевые различия:**
- B2B: RRP/MSRP, минимальные заказы, оптовые скидки
- B2C: акционные цены, рекомендации, отзывы
- Анонимные: базовая информация с призывом к регистрации

### 3. Cross-selling

**Стратегии увеличения продаж:**
- Релевантные связанные товары
- Отображение скидок и экономии
- Подготовка к "Часто покупают вместе"

## Будущие улучшения

### Краткосрочные (следующие 2-4 недели)
1. Интеграция с Favorites API (статус избранного)
2. Отзывы и рейтинги товаров
3. Вариации товаров (размеры, цвета)

### Среднесрочные (1-3 месяца)
1. Персонализированные рекомендации
2. Просмотренные товары
3. Сравнение товаров

### Долгосрочные (3-6 месяцев)
1. AR/VR примерка для спортивной одежды
2. Видео-обзоры товаров
3. Live chat поддержка на странице товара

## Заключение

Story 2.5 создала полноценную и информативную страницу товара для FREESPORT:

✅ **Comprehensive информация** - спецификации, изображения, цены, рекомендации  
✅ **Ролевая персонализация** - адаптация контента под тип пользователя  
✅ **SEO оптимизация** - структурированные данные и метатеги  
✅ **Performance готовность** - оптимизированные запросы и кэширование  
✅ **Cross-selling механизмы** - связанные товары и ценовая мотивация  

Product Detail API обеспечивает всю необходимую информацию для принятия решения о покупке и готов к интеграции с корзиной и системой заказов.