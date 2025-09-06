# Паттерн: Ролевое ценообразование

## Описание

Ключевой архитектурный паттерн FREESPORT для поддержки B2B/B2C модели продаж с различными уровнями цен в зависимости от роли пользователя.

## Роли пользователей

```python
ROLE_CHOICES = [
    ('retail', 'Розничный покупатель'),           # Обычные покупатели
    ('wholesale_level1', 'Оптовик уровень 1'),    # Мелкий опт
    ('wholesale_level2', 'Оптовик уровень 2'),    # Средний опт  
    ('wholesale_level3', 'Оптовик уровень 3'),    # Крупный опт
    ('trainer', 'Тренер'),                        # Тренеры спортклубов
    ('federation_rep', 'Представитель федерации'), # Спортивные федерации
    ('admin', 'Администратор'),                   # Системные админы
]
```

## Реализация в модели Product

### Поля цен

```python
class Product(models.Model):
    # Основная цена (всегда есть)
    retail_price = models.DecimalField("Розничная цена", max_digits=10, decimal_places=2)
    
    # Оптовые цены (nullable - могут отсутствовать)
    opt1_price = models.DecimalField("Оптовая цена 1", max_digits=10, decimal_places=2, null=True, blank=True)
    opt2_price = models.DecimalField("Оптовая цена 2", max_digits=10, decimal_places=2, null=True, blank=True)  
    opt3_price = models.DecimalField("Оптовая цена 3", max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Специальные цены
    trainer_price = models.DecimalField("Цена для тренера", max_digits=10, decimal_places=2, null=True, blank=True)
    federation_price = models.DecimalField("Цена для федерации", max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Информационные цены для B2B (не для продажи)
    recommended_retail_price = models.DecimalField("RRP", max_digits=10, decimal_places=2, null=True, blank=True)
    max_suggested_retail_price = models.DecimalField("MSRP", max_digits=10, decimal_places=2, null=True, blank=True)
```

### Бизнес-логика

```python
def get_price_for_user(self, user):
    """
    Получить цену товара для конкретного пользователя на основе его роли
    
    ПРИНЦИПЫ:
    1. Fallback к retail_price если специальной цены нет
    2. Анонимные пользователи получают retail_price  
    3. Admins получают retail_price (не льготные цены)
    """
    if not user or not user.is_authenticated:
        return self.retail_price

    role_price_mapping = {
        "retail": self.retail_price,
        "wholesale_level1": self.opt1_price or self.retail_price,
        "wholesale_level2": self.opt2_price or self.retail_price, 
        "wholesale_level3": self.opt3_price or self.retail_price,
        "trainer": self.trainer_price or self.retail_price,
        "federation_rep": self.federation_price or self.retail_price,
        "admin": self.retail_price,  # Админы НЕ получают льготы
    }

    return role_price_mapping.get(user.role, self.retail_price)
```

## Применение в API

### ProductSerializer

```python
class ProductSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    
    def get_price(self, obj):
        """Цена с учетом роли пользователя из запроса"""
        request = self.context.get('request')
        user = request.user if request else None
        return obj.get_price_for_user(user)
```

### Frontend использование

```typescript
interface Product {
  id: number;
  name: string;
  price: number;  // Уже учитывает роль пользователя
  retail_price?: number;  // Только для B2B (показать экономию)
  recommended_retail_price?: number;  // RRP для B2B
}

// Компонент цены
const PriceDisplay: React.FC<{product: Product, userRole: string}> = ({product, userRole}) => {
  const showDiscount = userRole !== 'retail' && product.retail_price && product.price < product.retail_price;
  
  return (
    <div className="price-container">
      <span className="current-price text-2xl font-bold text-blue-600">
        {product.price.toLocaleString('ru-RU')} ₽
      </span>
      
      {showDiscount && (
        <span className="retail-price text-sm text-gray-500 line-through ml-2">
          {product.retail_price.toLocaleString('ru-RU')} ₽
        </span>
      )}
    </div>
  );
};
```

## Фильтрация по ценам

### Django Filter

```python
class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(method='filter_by_min_price')
    max_price = django_filters.NumberFilter(method='filter_by_max_price')
    
    def filter_by_min_price(self, queryset, name, value):
        """Фильтрация по минимальной цене с учетом роли"""
        user = self.request.user
        if not user.is_authenticated:
            return queryset.filter(retail_price__gte=value)
        
        # Сложная логика для разных ролей
        if user.role == 'wholesale_level1':
            return queryset.filter(
                Q(opt1_price__gte=value) | 
                Q(opt1_price__isnull=True, retail_price__gte=value)
            )
        # ... аналогично для других ролей
        
        return queryset.filter(retail_price__gte=value)
```

## Тестирование

### Обязательные тесты

```python
@pytest.mark.parametrize("role,expected_price", [
    ('retail', Decimal('1000.00')),
    ('wholesale_level1', Decimal('800.00')), 
    ('wholesale_level2', Decimal('750.00')),
    ('trainer', Decimal('900.00')),
    ('federation_rep', Decimal('700.00')),
])
def test_role_based_pricing(role, expected_price):
    """Тест ролевого ценообразования"""
    user = UserFactory(role=role)
    product = ProductFactory(
        retail_price=Decimal('1000.00'),
        opt1_price=Decimal('800.00'),
        opt2_price=Decimal('750.00'),
        trainer_price=Decimal('900.00'), 
        federation_price=Decimal('700.00')
    )
    
    assert product.get_price_for_user(user) == expected_price

def test_price_fallback_to_retail():
    """Fallback к retail_price если специальной цены нет"""
    user = UserFactory(role='wholesale_level1')
    product = ProductFactory(
        retail_price=Decimal('1000.00'),
        opt1_price=None  # Нет оптовой цены
    )
    
    assert product.get_price_for_user(user) == Decimal('1000.00')
```

## Миграции

### Добавление новой роли

```python
# Добавить в User.ROLE_CHOICES новую роль
# Затем создать миграцию:

def add_new_price_field(apps, schema_editor):
    """Добавляет новое поле цены для новой роли"""
    pass

def reverse_add_new_price_field(apps, schema_editor):
    """Откат изменений"""
    pass

class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='product', 
            name='new_role_price',
            field=models.DecimalField('Цена для новой роли', max_digits=10, decimal_places=2, null=True, blank=True)
        ),
        migrations.RunPython(add_new_price_field, reverse_add_new_price_field),
    ]
```

## Лучшие практики

### ✅ Что НУЖНО делать

1. **Всегда fallback к retail_price** если специальной цены нет
2. **Тестировать все роли** в unit тестах 
3. **Валидировать цены** - оптовые не могут быть выше розничных
4. **Логировать ценообразование** в критических местах
5. **Кэшировать цены** для частых запросов

### ❌ Что НЕ нужно делать

1. **Не хардкодить роли** в коде - использовать константы
2. **Не показывать все цены** неавторизованным пользователям
3. **Не давать льготы админам** без явного бизнес-требования  
4. **Не забывать про nullable поля** при добавлении новых ролей
5. **Не игнорировать миграции данных** при изменении ролей

## Интеграция с внешними системами

### 1С интеграция

```python
# При синхронизации с 1С учитывать ролевые цены
class OneCProductSync:
    def sync_product_prices(self, onec_data):
        """Синхронизация цен из 1С"""
        product = Product.objects.get(onec_id=onec_data['id'])
        
        # Маппинг ролей 1С на роли Django
        price_mapping = {
            'retail': onec_data.get('retail_price'),
            'opt1': onec_data.get('wholesale_level1_price'),
            'opt2': onec_data.get('wholesale_level2_price'),
            # ...
        }
        
        for role, price in price_mapping.items():
            if price:
                setattr(product, f'{role}_price', Decimal(str(price)))
        
        product.save()
```

Этот паттерн является основополагающим для всей бизнес-модели FREESPORT!