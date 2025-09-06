# Паттерн: Дедупликация корзины

## Описание

Паттерн предотвращения дублирования товаров в корзине покупок. В FREESPORT один товар может быть только в одной позиции корзины - при повторном добавлении увеличивается количество.

## Архитектура

### Модели базы данных

```python
class Cart(models.Model):
    """Корзина покупок"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='cart'
    )
    session_key = models.CharField("Ключ сессии", max_length=40, null=True, blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        db_table = "cart"
        # ✅ ПАТТЕРН: Уникальность корзины по пользователю ИЛИ сессии
        constraints = [
            models.CheckConstraint(
                check=Q(user__isnull=False) | Q(session_key__isnull=False),
                name="cart_must_have_user_or_session"
            )
        ]

class CartItem(models.Model):
    """Позиция в корзине"""
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField("Количество", default=1)
    
    # ✅ Снимок цены на момент добавления в корзину
    price_snapshot = models.DecimalField(
        "Цена на момент добавления", 
        max_digits=10, 
        decimal_places=2
    )
    
    created_at = models.DateTimeField("Дата добавления", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        db_table = "cart_items"
        # ✅ КЛЮЧЕВОЙ ПАТТЕРН: Уникальность товара в корзине
        unique_together = ('cart', 'product')
        indexes = [
            models.Index(fields=['cart', 'product']),
        ]
```

### Бизнес-логика дедупликации

```python
class CartService:
    """Сервис управления корзиной с дедупликацией"""
    
    def add_item(self, cart, product, quantity=1, user=None):
        """
        Добавление товара в корзину с дедупликацией
        
        ЛОГИКА:
        1. Если товар уже есть - увеличиваем количество
        2. Если товара нет - создаем новую позицию
        3. Сохраняем снимок цены на момент добавления
        """
        try:
            # Попытка найти существующую позицию
            cart_item = CartItem.objects.get(cart=cart, product=product)
            
            # ✅ ДЕДУПЛИКАЦИЯ: Увеличиваем количество
            cart_item.quantity += quantity
            cart_item.save()
            
            return cart_item, False  # False = не создан новый
            
        except CartItem.DoesNotExist:
            # ✅ Создаем новую позицию с снимком цены
            current_price = product.get_price_for_user(user)
            
            cart_item = CartItem.objects.create(
                cart=cart,
                product=product, 
                quantity=quantity,
                price_snapshot=current_price
            )
            
            return cart_item, True  # True = создан новый
    
    def update_item_quantity(self, cart, product, quantity):
        """
        Обновление количества товара
        
        ЛОГИКА:
        - quantity = 0 → удаляем позицию
        - quantity > 0 → обновляем количество
        """
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            
            if quantity <= 0:
                cart_item.delete()
                return None
            else:
                cart_item.quantity = quantity
                cart_item.save()
                return cart_item
                
        except CartItem.DoesNotExist:
            if quantity > 0:
                # Создаем новую позицию если её не было
                return self.add_item(cart, product, quantity)[0]
            return None

    def merge_carts(self, anonymous_cart, user_cart):
        """
        Слияние анонимной корзины с пользовательской
        При авторизации пользователя
        """
        for item in anonymous_cart.items.all():
            self.add_item(
                cart=user_cart,
                product=item.product,
                quantity=item.quantity,
                user=user_cart.user
            )
        
        # Удаляем анонимную корзину
        anonymous_cart.delete()
```

## API реализация

### ViewSet для корзины

```python
class CartItemViewSet(viewsets.ModelViewSet):
    """API для управления позициями корзины"""
    
    permission_classes = [permissions.AllowAny]  # Поддержка анонимных корзин
    
    def get_queryset(self):
        cart = self.get_or_create_cart()
        return CartItem.objects.filter(cart=cart).select_related('product', 'product__brand')
    
    def get_or_create_cart(self):
        """Получение или создание корзины для пользователя/сессии"""
        if self.request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=self.request.user)
        else:
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            cart, created = Cart.objects.get_or_create(session_key=session_key)
        
        return cart
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """
        Добавление товара в корзину
        POST /api/cart/add_item/
        {
            "product_id": 123,
            "quantity": 2
        }
        """
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            cart = self.get_or_create_cart()
            
            cart_service = CartService()
            cart_item, created = cart_service.add_item(
                cart=cart,
                product=product,
                quantity=quantity,
                user=request.user if request.user.is_authenticated else None
            )
            
            serializer = CartItemSerializer(cart_item)
            
            return Response({
                'item': serializer.data,
                'created': created,
                'total_items': cart.items.count(),
                'cart_total': cart.get_total_price()
            })
            
        except Product.DoesNotExist:
            return Response(
                {'error': 'Товар не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['patch'])
    def update_quantity(self, request, pk=None):
        """
        Обновление количества товара
        PATCH /api/cart/{product_id}/update_quantity/
        {
            "quantity": 5
        }
        """
        quantity = int(request.data.get('quantity', 1))
        cart = self.get_or_create_cart()
        
        try:
            product = Product.objects.get(id=pk)
            cart_service = CartService()
            
            cart_item = cart_service.update_item_quantity(cart, product, quantity)
            
            if cart_item:
                serializer = CartItemSerializer(cart_item)
                return Response(serializer.data)
            else:
                return Response({'message': 'Товар удален из корзины'})
                
        except Product.DoesNotExist:
            return Response(
                {'error': 'Товар не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
```

## Frontend реализация

### React Hook для корзины

```typescript
interface CartItem {
  id: number;
  product: Product;
  quantity: number;
  price_snapshot: number;
}

const useCart = () => {
  const [items, setItems] = useState<CartItem[]>([]);
  const [loading, setLoading] = useState(false);
  
  const addItem = async (productId: number, quantity: number = 1) => {
    setLoading(true);
    
    try {
      const response = await fetch('/api/cart/add_item/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: productId, quantity })
      });
      
      const data = await response.json();
      
      if (data.created) {
        // ✅ Новая позиция
        setItems(prev => [...prev, data.item]);
      } else {
        // ✅ ДЕДУПЛИКАЦИЯ: Обновляем существующую позицию
        setItems(prev => prev.map(item => 
          item.product.id === productId 
            ? { ...item, quantity: data.item.quantity }
            : item
        ));
      }
      
      // Уведомление пользователя
      toast.success(
        data.created 
          ? 'Товар добавлен в корзину'
          : 'Количество товара обновлено'
      );
      
    } catch (error) {
      toast.error('Ошибка добавления товара');
    } finally {
      setLoading(false);
    }
  };
  
  const updateQuantity = async (productId: number, quantity: number) => {
    // ✅ Оптимистичное обновление UI
    setItems(prev => prev.map(item =>
      item.product.id === productId
        ? { ...item, quantity }
        : item
    ));
    
    try {
      await fetch(`/api/cart/${productId}/update_quantity/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity })
      });
    } catch (error) {
      // Откат изменений при ошибке
      loadCartItems();
      toast.error('Ошибка обновления количества');
    }
  };
  
  return { items, addItem, updateQuantity, loading };
};
```

### Компонент счетчика количества

```tsx
const QuantityCounter: React.FC<{
  productId: number;
  currentQuantity: number;
  onUpdate: (quantity: number) => void;
}> = ({ productId, currentQuantity, onUpdate }) => {
  
  const handleDecrease = () => {
    const newQuantity = Math.max(0, currentQuantity - 1);
    onUpdate(newQuantity);
  };
  
  const handleIncrease = () => {
    onUpdate(currentQuantity + 1);
  };
  
  return (
    <div className="flex items-center space-x-2">
      <button 
        onClick={handleDecrease}
        className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300"
        disabled={currentQuantity <= 1}
      >
        -
      </button>
      
      <span className="w-8 text-center font-medium">
        {currentQuantity}
      </span>
      
      <button
        onClick={handleIncrease} 
        className="w-8 h-8 rounded-full bg-blue-600 text-white hover:bg-blue-700"
      >
        +
      </button>
    </div>
  );
};
```

## Тестирование

### Unit тесты дедупликации

```python
class TestCartDeduplication:
    
    @pytest.mark.unit
    def test_add_same_product_twice(self):
        """Добавление одного товара дважды увеличивает количество"""
        cart = CartFactory()
        product = ProductFactory()
        service = CartService()
        
        # Первое добавление
        item1, created1 = service.add_item(cart, product, quantity=2)
        assert created1 is True
        assert item1.quantity == 2
        
        # Второе добавление того же товара
        item2, created2 = service.add_item(cart, product, quantity=3)
        assert created2 is False  # Не создан новый
        assert item2.id == item1.id  # Тот же объект
        assert item2.quantity == 5  # 2 + 3
        
        # В корзине только одна позиция
        assert cart.items.count() == 1
    
    @pytest.mark.unit 
    def test_unique_constraint_violation(self):
        """Прямое создание дубликата должно вызывать ошибку"""
        cart = CartFactory()
        product = ProductFactory()
        
        # Создаем первую позицию
        CartItem.objects.create(cart=cart, product=product, quantity=1, price_snapshot=100)
        
        # Попытка создать дубликат напрямую
        with pytest.raises(IntegrityError):
            CartItem.objects.create(cart=cart, product=product, quantity=1, price_snapshot=100)
```

### API тесты

```python
class TestCartAPI:
    
    @pytest.mark.integration
    def test_add_item_deduplication(self, api_client):
        """API дедупликация при добавлении товара"""
        product = ProductFactory(retail_price=1000)
        
        # Первый запрос
        response1 = api_client.post('/api/cart/add_item/', {
            'product_id': product.id,
            'quantity': 2
        })
        
        assert response1.status_code == 201
        data1 = response1.json()
        assert data1['created'] is True
        assert data1['item']['quantity'] == 2
        
        # Второй запрос с тем же товаром
        response2 = api_client.post('/api/cart/add_item/', {
            'product_id': product.id, 
            'quantity': 1
        })
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2['created'] is False  # Не создан новый
        assert data2['item']['quantity'] == 3  # 2 + 1
        assert data2['total_items'] == 1  # Всего позиций в корзине
```

## Лучшие практики

### ✅ Что НУЖНО делать

1. **Использовать unique_together** для предотвращения дубликатов на уровне БД
2. **Сохранять снимок цены** на момент добавления в корзину  
3. **Поддерживать анонимные корзины** через session_key
4. **Реализовать слияние корзин** при авторизации
5. **Валидировать количество** перед добавлением

### ❌ Что НЕ нужно делать

1. **Не полагаться только на frontend валидацию** - дубликаты могут появиться
2. **Не игнорировать race conditions** при одновременных запросах
3. **Не забывать про очистку старых корзин** анонимных пользователей
4. **Не обновлять цены в корзине автоматически** - только по запросу пользователя

## Производительность

### Оптимизация запросов

```python
# ✅ ХОРОШО: Предзагрузка связанных объектов
cart_items = CartItem.objects.filter(cart=cart)\
    .select_related('product', 'product__brand', 'product__category')\
    .order_by('created_at')

# ❌ ПЛОХО: N+1 запросы
for item in cart_items:
    print(item.product.name)  # Отдельный запрос к БД
    print(item.product.brand.name)  # Еще один запрос
```

### Кэширование корзины

```python
def get_cart_total_cached(cart_id):
    """Кэширование общей суммы корзины"""
    cache_key = f"cart_total_{cart_id}"
    total = cache.get(cache_key)
    
    if total is None:
        total = CartItem.objects.filter(cart_id=cart_id)\
            .aggregate(total=Sum('price_snapshot'))['total'] or 0
        cache.set(cache_key, total, timeout=300)  # 5 минут
    
    return total
```

Этот паттерн обеспечивает корректную работу корзины и предотвращает проблемы с дублированием товаров!