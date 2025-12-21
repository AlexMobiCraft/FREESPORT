# Проверка вариантов с Да в size_value
from apps.products.models import ProductVariant

# Найти все варианты с невалидным size_value
invalid = ProductVariant.objects.filter(size_value__iexact='Да')
print(f"Найдено вариантов с size_value='Да': {invalid.count()}")

for v in invalid[:10]:
    print(f"  {v.sku}: size_value=[{v.size_value}], product={v.product.name if v.product else None}")
