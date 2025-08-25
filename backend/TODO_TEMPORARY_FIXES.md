# Временные заглушки и TODO для будущих исправлений

## Story 2.3: Personal Cabinet API

### Временные заглушки требующие исправления:

#### 1. UserDashboardView - заглушки для статистики заказов
**Файл:** `apps/users/views.py` - UserDashboardView.get()
**Заглушки:**
```python
'orders_count': 0,  # Будет реализовано после создания Order модели
'total_order_amount': 0,  # Временно 0  
'avg_order_amount': 0,    # Временно 0
```
**Требует:** Реализации Order модели в apps/orders/models.py

#### 2. OrderHistoryView - полная заглушка
**Файл:** `apps/users/views.py` - OrderHistoryView.get()
**Заглушка:**
```python
return Response({
    'count': 0,
    'next': None, 
    'previous': None,
    'results': []
}, status=status.HTTP_200_OK)
```
**Требует:** 
- Реализации Order модели
- Подключения к реальным данным заказов
- Фильтрации по статусу и датам

#### 3. OrderHistorySerializer - заглушка serializer
**Файл:** `apps/users/serializers.py` - OrderHistorySerializer
**Статус:** Базовая структура создана, но не подключена к реальной модели
**Требует:** Обновления после создания Order модели

### Зависимости для исправления:

1. **Order модель** должна содержать поля:
   - id, order_number, status, total_amount, created_at, updated_at
   - связь с User через ForeignKey
   - связь с OrderItem для подсчета items_count

2. **OrderItem модель** для подсчета товаров в заказе

3. **Агрегация данных** для дашборда:
   - COUNT заказов пользователя  
   - SUM общей суммы заказов
   - AVG средней суммы заказа

### Статус исправления:
✅ **ГОТОВО К ИСПРАВЛЕНИЮ** - Story 2.7: Order API завершена 17 августа 2025

**Order модель реализована** в `apps/orders/models.py`:
- ✅ Все необходимые поля созданы: id, order_number, status, total_amount, created_at, updated_at
- ✅ ForeignKey связь с User установлена
- ✅ OrderItem модель создана для подсчета товаров в заказе
- ✅ Computed properties реализованы: total_items, calculated_total

**Готовые компоненты для интеграции:**
- ✅ `Order.objects.filter(user=user)` - фильтрация заказов по пользователю
- ✅ `order.total_items` - количество товаров в заказе  
- ✅ `order.calculated_total` - рассчитанная сумма заказа
- ✅ Агрегация доступна через Django ORM

**Следующий шаг:** Обновить заглушки в UserDashboardView и OrderHistoryView

### Поиск заглушек:
```bash
# Поиск всех временных заглушек
grep -r "Будет реализовано" backend/apps/users/
grep -r "Временно" backend/apps/users/
grep -r "заглушка" backend/apps/users/
```