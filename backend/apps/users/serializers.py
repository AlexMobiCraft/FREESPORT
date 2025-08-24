"""
Serializers для API управления пользователями
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from .models import User, Company, Address, Favorite


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer для регистрации новых пользователей
    """
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm', 'first_name', 'last_name',
            'phone', 'role', 'company_name', 'tax_id'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_email(self, value):
        """Проверка уникальности email"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return value.lower()

    def validate(self, attrs):
        """Валидация полей"""
        # Проверка совпадения паролей
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Пароли не совпадают.'
            })

        # Валидация B2B полей
        role = attrs.get('role', 'retail')
        if role != 'retail':
            # Для B2B пользователей требуется название компании
            if not attrs.get('company_name'):
                raise serializers.ValidationError({
                    'company_name': 'Название компании обязательно для B2B пользователей.'
                })
            
            # Для оптовиков и представителей федерации требуется ИНН
            if role.startswith('wholesale') or role == 'federation_rep':
                if not attrs.get('tax_id'):
                    raise serializers.ValidationError({
                        'tax_id': 'ИНН обязателен для оптовых покупателей и представителей федерации.'
                    })

        return attrs

    def create(self, validated_data):
        """Создание нового пользователя"""
        # Удаляем password_confirm из данных
        validated_data.pop('password_confirm')
        
        # Извлекаем пароль
        password = validated_data.pop('password')
        
        # Создаем пользователя
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        # B2B пользователи требуют верификации
        if user.role != 'retail':
            user.is_verified = False
            user.save()
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer для входа пользователя
    """
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, attrs):
        """Валидация данных для входа"""
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Аутентификация пользователя
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )

            if not user:
                raise serializers.ValidationError(
                    'Неверный email или пароль.',
                    code='authorization'
                )

            if not user.is_active:
                raise serializers.ValidationError(
                    'Аккаунт пользователя деактивирован.',
                    code='authorization'
                )

            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(
                'Необходимо указать email и пароль.',
                code='authorization'
            )


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer для просмотра и обновления профиля пользователя
    """
    full_name = serializers.CharField(read_only=True)
    is_b2b_user = serializers.BooleanField(read_only=True)
    is_wholesale_user = serializers.BooleanField(read_only=True)
    wholesale_level = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'company_name', 'tax_id', 'is_verified',
            'is_b2b_user', 'is_wholesale_user', 'wholesale_level',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'email', 'role', 'is_verified', 'created_at', 'updated_at'
        ]

    def validate_tax_id(self, value):
        """Валидация ИНН"""
        if value:
            # Простая валидация длины ИНН (10 или 12 цифр)
            if not value.isdigit() or len(value) not in [10, 12]:
                raise serializers.ValidationError(
                    'ИНН должен содержать 10 или 12 цифр.'
                )
        return value


class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer для адресов пользователя
    """
    full_address = serializers.CharField(read_only=True)

    class Meta:
        model = Address
        fields = [
            'id', 'user', 'address_type', 'full_name', 'phone', 'city',
            'street', 'building', 'apartment', 'postal_code',
            'is_default', 'full_address', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_postal_code(self, value):
        """Валидация почтового индекса"""
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError(
                'Почтовый индекс должен содержать 6 цифр.'
            )
        return value


class CompanySerializer(serializers.ModelSerializer):
    """
    Serializer для компании B2B пользователя
    """
    class Meta:
        model = Company
        fields = [
            'id', 'legal_name', 'tax_id', 'kpp', 'legal_address',
            'bank_name', 'bank_bik', 'account_number',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_tax_id(self, value):
        """Валидация ИНН компании"""
        if not value.isdigit() or len(value) not in [10, 12]:
            raise serializers.ValidationError(
                'ИНН должен содержать 10 или 12 цифр.'
            )
        return value

    def validate_kpp(self, value):
        """Валидация КПП"""
        if value and (not value.isdigit() or len(value) != 9):
            raise serializers.ValidationError(
                'КПП должен содержать 9 цифр.'
            )
        return value


class UserDashboardSerializer(serializers.Serializer):
    """
    Serializer для персонального дашборда пользователя
    """
    user_info = UserProfileSerializer(read_only=True)
    orders_count = serializers.IntegerField(read_only=True)
    favorites_count = serializers.IntegerField(read_only=True)
    addresses_count = serializers.IntegerField(read_only=True)
    
    # Дополнительная статистика для B2B
    total_order_amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True,
        required=False
    )
    avg_order_amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True,
        required=False
    )
    
    # Статус верификации для B2B
    verification_status = serializers.CharField(read_only=True, required=False)


class FavoriteSerializer(serializers.ModelSerializer):
    """
    Serializer для избранных товаров
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(
        source='product.retail_price', 
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    product_image = serializers.CharField(source='product.main_image', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = Favorite
        fields = [
            'id', 'product', 'product_name', 'product_price', 
            'product_image', 'product_slug', 'product_sku', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class FavoriteCreateSerializer(serializers.ModelSerializer):
    """
    Serializer для добавления товара в избранное
    """
    class Meta:
        model = Favorite
        fields = ['product']
    
    def validate_product(self, value):
        """Проверка существования товара"""
        from apps.products.models import Product
        
        if not Product.objects.filter(id=value.id, is_active=True).exists():
            raise serializers.ValidationError(
                'Товар не найден или недоступен.'
            )
        return value
    
    def validate(self, attrs):
        """Проверка на дублирование в избранном"""
        user = self.context['request'].user
        product = attrs['product']
        
        if Favorite.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError({
                'product': 'Товар уже добавлен в избранное.'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Создание записи в избранном"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class OrderHistorySerializer(serializers.Serializer):
    """
    Serializer для истории заказов пользователя
    (будет реализован после создания модели Order)
    """
    id = serializers.IntegerField(read_only=True)
    order_number = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    # Базовая информация о товарах в заказе
    order_items = serializers.ListField(
        child=serializers.DictField(),
        read_only=True
    )