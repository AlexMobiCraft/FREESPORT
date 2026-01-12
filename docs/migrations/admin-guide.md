# Admin Guide: ProductVariant Management

> **Story 13.4**: Миграция данных в production  
> **Version**: 1.0  
> **Last Updated**: 2025-12-02

## Обзор

Этот документ описывает управление системой ProductVariant для администраторов. После миграции на новую систему, товары имеют варианты (цвет, размер) с индивидуальными ценами и остатками.

---

## Структура данных

### Product (Товар)

Базовая информация о товаре:

| Поле | Описание |
|------|----------|
| `name` | Название товара |
| `slug` | URL-friendly идентификатор |
| `description` | Описание товара |
| `brand` | Бренд |
| `category` | Категория |
| `base_images` | Базовые изображения товара |
| `specifications` | Характеристики (JSON) |

### ProductVariant (Вариант товара)

Конкретный вариант товара с ценой и остатком:

| Поле | Описание |
|------|----------|
| `sku` | Артикул (уникальный) |
| `color_name` | Название цвета |
| `size_value` | Размер |
| `retail_price` | Розничная цена |
| `opt1_price` - `opt4_price` | Оптовые цены |
| `stock_quantity` | Остаток на складе |
| `main_image` | Основное изображение варианта |
| `gallery_images` | Галерея изображений |

### ColorMapping (Маппинг цветов)

Соответствие названий цветов из 1С и hex-кодов:

| Поле | Описание |
|------|----------|
| `name` | Название цвета из 1С |
| `hex_code` | Hex-код цвета (#RRGGBB) |
| `swatch_image` | Изображение образца (опционально) |

---

## ColorMapping Administration

### Просмотр цветов

1. Откройте Django Admin: `/admin/`
2. Перейдите в **Products → Color Mappings**
3. Просмотрите список цветов с hex-кодами

### Добавление нового цвета

1. Откройте Django Admin
2. Перейдите в **Products → Color Mappings**
3. Нажмите **Add Color Mapping**
4. Заполните поля:
   - **Name**: Название цвета из 1С (точное соответствие!)
   - **Hex code**: Hex-код цвета (например, `#FF5733`)
   - **Swatch image**: Изображение образца (опционально)
5. Нажмите **Save**

### Базовые цвета (20 штук)

После миграции в системе должны быть следующие базовые цвета:

| Название | Hex-код |
|----------|---------|
| Белый | #FFFFFF |
| Черный | #000000 |
| Красный | #FF0000 |
| Синий | #0000FF |
| Зеленый | #008000 |
| Желтый | #FFFF00 |
| Оранжевый | #FFA500 |
| Розовый | #FFC0CB |
| Фиолетовый | #800080 |
| Серый | #808080 |
| Коричневый | #A52A2A |
| Бежевый | #F5F5DC |
| Голубой | #00BFFF |
| Бирюзовый | #40E0D0 |
| Бордовый | #800020 |
| Хаки | #C3B091 |
| Золотой | #FFD700 |
| Серебряный | #C0C0C0 |
| Мультиколор | #GRADIENT |
| Камуфляж | #78866B |

### Проверка ColorMapping

```bash
# Через Django shell
python manage.py shell -c "
from apps.products.models import ColorMapping
colors = ColorMapping.objects.all()
print(f'Total colors: {colors.count()}')
for c in colors:
    print(f'  {c.name}: {c.hex_code}')
"
```

---

## Проверка импорта из 1С

### Статус последнего импорта

```bash
# Через Django shell
python manage.py shell << 'EOF'
from apps.products.models import ImportSession
session = ImportSession.objects.order_by('-started_at').first()
if session:
    print(f"Session: {session.id}")
    print(f"Started: {session.started_at}")
    print(f"Finished: {session.finished_at}")
    print(f"Status: {session.status}")
    print(f"Products created: {session.products_created}")
    print(f"Products updated: {session.products_updated}")
    print(f"Variants created: {session.variants_created}")
    print(f"Variants updated: {session.variants_updated}")
    print(f"Errors: {session.errors_count}")
EOF
```

### Проверка количества записей

```bash
python manage.py shell << 'EOF'
from apps.products.models import Product, ProductVariant, ColorMapping, Brand, Category

print("=== Database Statistics ===")
print(f"Products: {Product.objects.count()}")
print(f"  - Active: {Product.objects.filter(is_active=True).count()}")
print(f"  - Inactive: {Product.objects.filter(is_active=False).count()}")
print(f"ProductVariants: {ProductVariant.objects.count()}")
print(f"  - In stock: {ProductVariant.objects.filter(stock_quantity__gt=0).count()}")
print(f"  - Out of stock: {ProductVariant.objects.filter(stock_quantity=0).count()}")
print(f"ColorMappings: {ColorMapping.objects.count()}")
print(f"Brands: {Brand.objects.count()}")
print(f"Categories: {Category.objects.count()}")
EOF
```

### Проверка товаров без вариантов

```bash
python manage.py shell << 'EOF'
from apps.products.models import Product

products_without_variants = Product.objects.filter(variants__isnull=True)
count = products_without_variants.count()

print(f"Products without variants: {count}")
if count > 0:
    print("Examples:")
    for p in products_without_variants[:10]:
        print(f"  - {p.name} (ID: {p.id})")
EOF
```

### Проверка вариантов без цвета

```bash
python manage.py shell << 'EOF'
from apps.products.models import ProductVariant

variants_without_color = ProductVariant.objects.filter(color_name='')
count = variants_without_color.count()

print(f"Variants without color: {count}")
if count > 0:
    print("Examples:")
    for v in variants_without_color[:10]:
        print(f"  - {v.sku}: {v.product.name}")
EOF
```

---

## Ручной запуск импорта

### Полный импорт

```bash
# Полный импорт каталога
python manage.py import_products_from_1c --full

# С verbose логированием
python manage.py import_products_from_1c --full --verbosity=2
```

### Инкрементальный импорт

```bash
# Только изменения с последнего импорта
python manage.py import_products_from_1c
```

### Импорт только цен

```bash
# Обновить только цены
python manage.py import_products_from_1c --prices-only
```

### Импорт только остатков

```bash
# Обновить только остатки
python manage.py import_products_from_1c --stocks-only
```

---

## FAQ по ProductVariant

### Q: Почему товар не отображается на сайте?

**A:** Проверьте:
1. `is_active = True` у Product
2. Есть хотя бы один ProductVariant
3. ProductVariant имеет `stock_quantity > 0` (если фильтр "в наличии")

```bash
python manage.py shell << 'EOF'
from apps.products.models import Product
p = Product.objects.get(slug='your-product-slug')
print(f"Active: {p.is_active}")
print(f"Variants: {p.variants.count()}")
for v in p.variants.all():
    print(f"  - {v.sku}: stock={v.stock_quantity}, price={v.retail_price}")
EOF
```

### Q: Почему цена отображается неправильно?

**A:** Цена зависит от роли пользователя:
- Анонимный/Retail → `retail_price`
- Оптовик Level 1 → `opt1_price` (или `retail_price` если null)
- Оптовик Level 2 → `opt2_price`
- и т.д.

Проверьте что у варианта заполнены нужные цены:

```bash
python manage.py shell << 'EOF'
from apps.products.models import ProductVariant
v = ProductVariant.objects.get(sku='YOUR-SKU')
print(f"retail_price: {v.retail_price}")
print(f"opt1_price: {v.opt1_price}")
print(f"opt2_price: {v.opt2_price}")
print(f"opt3_price: {v.opt3_price}")
print(f"opt4_price: {v.opt4_price}")
EOF
```

### Q: Почему цвет не отображается?

**A:** Проверьте что цвет есть в ColorMapping:

```bash
python manage.py shell << 'EOF'
from apps.products.models import ColorMapping, ProductVariant

# Найти вариант
v = ProductVariant.objects.get(sku='YOUR-SKU')
print(f"Color name: '{v.color_name}'")

# Проверить маппинг
mapping = ColorMapping.objects.filter(name=v.color_name).first()
if mapping:
    print(f"Hex code: {mapping.hex_code}")
else:
    print("WARNING: Color not found in ColorMapping!")
    print("Add it via Django Admin: /admin/products/colormapping/add/")
EOF
```

### Q: Как добавить новый вариант товара?

**A:** Через Django Admin:

1. Откройте `/admin/products/productvariant/add/`
2. Выберите Product
3. Заполните:
   - SKU (уникальный артикул)
   - Color name (должен быть в ColorMapping)
   - Size value
   - Retail price
   - Stock quantity
4. Сохраните

### Q: Как массово обновить цены?

**A:** Запустите импорт только цен:

```bash
python manage.py import_products_from_1c --prices-only
```

Или через Django Admin → ProductVariant → выберите записи → Action: "Update prices".

### Q: Как найти товары с нулевым остатком?

```bash
python manage.py shell << 'EOF'
from apps.products.models import ProductVariant

out_of_stock = ProductVariant.objects.filter(stock_quantity=0)
print(f"Out of stock variants: {out_of_stock.count()}")

# Группировка по товарам
from django.db.models import Count
products = out_of_stock.values('product__name').annotate(count=Count('id')).order_by('-count')[:20]
for p in products:
    print(f"  {p['product__name']}: {p['count']} variants")
EOF
```

---

## Логи и мониторинг

### Логи импорта

```bash
# Последние 100 строк лога импорта
tail -100 /var/log/freesport/import_products.log

# Поиск ошибок
grep "ERROR" /var/log/freesport/import_products.log

# Поиск warnings
grep "WARNING" /var/log/freesport/import_products.log
```

### Мониторинг API

```bash
# Проверка endpoint товаров
curl -s http://localhost:8000/api/products/ | jq '.count'

# Проверка конкретного товара с вариантами
curl -s http://localhost:8000/api/products/some-slug/ | jq '.variants'
```

---

## Контакты поддержки

| Вопрос | Контакт |
|--------|---------|
| Проблемы с импортом | Slack: #backend |
| Проблемы с отображением | Slack: #frontend |
| Проблемы с сервером | Slack: #devops |

---

## Revision History

| Дата | Версия | Описание | Автор |
|------|--------|----------|-------|
| 2025-12-02 | 1.0 | Создание документа | James (Dev) |
