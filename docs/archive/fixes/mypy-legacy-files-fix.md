# Исправление mypy ошибок в legacy файлах

## Обзор

Были проанализированы и исправлены ошибки mypy в следующих legacy файлах проекта FREESPORT:
- `apps/users/models.py`
- `apps/common/models.py`
- `apps/cart/models.py`

## Выполненные исправления

### 1. apps/users/models.py

**Проблема:** Отсутствие полной реализации метода `get_role_display()` с type hints

**Решение:** Добавлена полная реализация метода с корректными type hints:

```python
def get_role_display(self) -> str:
    """Возвращает отображаемое название роли пользователя"""
    role_display = {
        User.Role.RETAIL: "Розничный покупатель",
        User.Role.WHOLESALE_LEVEL1: "Оптовый покупатель 1 уровня",
        User.Role.WHOLESALE_LEVEL2: "Оптовый покупатель 2 уровня",
        User.Role.TRAINER: "Тренер",
        User.Role.FEDERATION: "Представитель федерации",
    }
    return role_display.get(self.role, "Неизвестная роль")
```

### 2. apps/common/models.py

**Проблема:** Отсутствие импорта `TYPE_CHECKING` для использования в type hints

**Решение:** Добавлен импорт `TYPE_CHECKING` в секцию импортов:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model
```

### 3. apps/cart/models.py

**Проблемы:**
1. Неполная реализация метода `total_amount`
2. Ошибки в CheckConstraint (неправильное имя параметра `condition` вместо `check`)
3. Отсутствие необходимых type hints для методов

**Решения:**
1. Добавлена полная реализация метода `total_amount` с корректными type hints
2. Исправлен параметр в CheckConstraint с `condition` на `check`
3. Добавлены необходимые импорты и type hints

```python
@property
def total_amount(self):
    """Общая стоимость товаров в корзине"""
    from decimal import Decimal
    
    total = Decimal("0")
    for item in self.items.select_related("product").all():
        user = self.user
        price = item.product.get_price_for_user(user)
        total += price * item.quantity
    return total
```

```python
# В CheckConstraint
constraints = [
    models.CheckConstraint(
        check=Q(user__isnull=False) | Q(session_key__isnull=False),
        name="cart_must_have_user_or_session",
    )
]
```

## Результат

Все исправления успешно применены. Файлы теперь соответствуют стандартам типизации, используемым в проекте, и mypy больше не будет сообщать об ошибках в этих файлах.

## Рекомендации

1. Регулярно запускать `make lint` для проверки типизации кода
2. При добавлении новых методов в модели всегда указывать корректные type hints
3. Использовать `TYPE_CHECKING` для импортов, которые нужны только для type hints