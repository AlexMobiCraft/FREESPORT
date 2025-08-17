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

### Когда исправлять:
- После реализации Story 2.7: Order API
- Все заглушки помечены комментариями для быстрого поиска

### Поиск заглушек:
```bash
# Поиск всех временных заглушек
grep -r "Будет реализовано" backend/apps/users/
grep -r "Временно" backend/apps/users/
grep -r "заглушка" backend/apps/users/
```