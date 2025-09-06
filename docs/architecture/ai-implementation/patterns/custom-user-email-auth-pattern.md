# Паттерн: Кастомная User модель с email аутентификацией

## Описание

Паттерн замены стандартной Django аутентификации с username на аутентификацию по email, специально настроенный для FREESPORT с поддержкой ролевой системы B2B/B2C.

## Архитектура

### Кастомная User модель

```python
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """
    Кастомный менеджер пользователей для email аутентификации
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """Создание обычного пользователя"""
        if not email:
            raise ValueError("Email обязателен для создания пользователя")
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Создание суперпользователя"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Кастомная модель пользователя с email аутентификацией и ролевой системой
    """
    
    # ✅ КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Отключаем username, используем email
    username = None  # Полностью убираем поле username
    email = models.EmailField("Email", unique=True)
    
    # ✅ РОЛЕВАЯ СИСТЕМА для B2B/B2C
    ROLE_CHOICES = [
        ('retail', 'Розничный покупатель'),
        ('wholesale_level1', 'Оптовик уровень 1'),
        ('wholesale_level2', 'Оптовик уровень 2'), 
        ('wholesale_level3', 'Оптовик уровень 3'),
        ('trainer', 'Тренер'),
        ('federation_rep', 'Представитель федерации'),
        ('admin', 'Администратор'),
    ]
    role = models.CharField("Роль", max_length=20, choices=ROLE_CHOICES, default='retail')
    
    # ✅ B2B специфичные поля
    company_name = models.CharField("Название компании", max_length=200, blank=True)
    tax_id = models.CharField("ИНН", max_length=20, blank=True)
    is_verified = models.BooleanField("Верифицированный B2B клиент", default=False)
    
    # ✅ Дополнительные поля профиля
    phone = models.CharField("Телефон", max_length=20, blank=True)
    date_of_birth = models.DateField("Дата рождения", null=True, blank=True)
    
    # ✅ Стандартные поля аудита
    created_at = models.DateTimeField("Дата регистрации", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)
    
    # ✅ НАСТРОЙКА АУТЕНТИФИКАЦИИ
    objects = UserManager()
    USERNAME_FIELD = 'email'  # Используем email вместо username
    REQUIRED_FIELDS = []  # При создании superuser потребуется только email
    
    class Meta:
        db_table = 'users_user'  # Кастомное имя таблицы
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_verified', 'role']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    @property
    def full_name(self):
        """Полное имя пользователя"""
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    @property
    def is_b2b_user(self):
        """Является ли пользователь B2B клиентом"""
        return self.role in ['wholesale_level1', 'wholesale_level2', 'wholesale_level3', 'trainer', 'federation_rep']
    
    def get_price_level(self):
        """Получить уровень ценообразования для пользователя"""
        price_levels = {
            'retail': 'retail',
            'wholesale_level1': 'opt1', 
            'wholesale_level2': 'opt2',
            'wholesale_level3': 'opt3',
            'trainer': 'trainer',
            'federation_rep': 'federation',
            'admin': 'retail',  # Админы получают розничные цены
        }
        return price_levels.get(self.role, 'retail')
```

### Настройка в settings.py

```python
# settings/base.py

# ✅ КРИТИЧЕСКИ ВАЖНО: Указать кастомную модель пользователя
AUTH_USER_MODEL = 'users.User'

# ✅ JWT настройки для email аутентификации
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    
    # Поля для JWT токена
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    # Кастомные claims
    'TOKEN_OBTAIN_SERIALIZER': 'apps.users.serializers.CustomTokenObtainPairSerializer',
}

# ✅ Email backend для отправки писем
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
```

## Аутентификация и регистрация

### JWT Serializer с ролями

```python
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Кастомный serializer JWT токена с дополнительными claims
    """
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # ✅ Добавляем роль в JWT токен
        token['role'] = user.role
        token['is_verified'] = user.is_verified
        token['full_name'] = user.full_name
        
        return token
    
    def validate(self, attrs):
        """Валидация с дополнительной информацией о пользователе"""
        data = super().validate(attrs)
        
        # Добавляем информацию о пользователе в ответ
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'role': self.user.role,
            'full_name': self.user.full_name,
            'is_verified': self.user.is_verified,
        }
        
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer для регистрации пользователя"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm', 
            'first_name', 'last_name', 'phone', 
            'role', 'company_name', 'tax_id'
        ]
    
    def validate_email(self, value):
        """Проверка уникальности email"""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value.lower()
    
    def validate(self, data):
        """Общая валидация"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Пароли не совпадают")
        
        # B2B пользователи должны указать название компании
        if data.get('role') in ['wholesale_level1', 'wholesale_level2', 'wholesale_level3']:
            if not data.get('company_name'):
                raise serializers.ValidationError("B2B пользователи должны указать название компании")
        
        return data
    
    def create(self, validated_data):
        """Создание пользователя"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(password=password, **validated_data)
        return user
```

### ViewSet для аутентификации

```python
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string


class AuthViewSet(viewsets.GenericViewSet):
    """ViewSet для аутентификации и управления аккаунтом"""
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        """
        Регистрация нового пользователя
        POST /api/auth/register/
        """
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # ✅ Отправляем email подтверждения
            self.send_verification_email(user)
            
            return Response({
                'message': 'Регистрация успешна. Проверьте email для подтверждения.',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def verify_email(self, request):
        """
        Подтверждение email адреса
        POST /api/auth/verify-email/
        """
        user_id = request.data.get('user_id')
        token = request.data.get('token')
        
        try:
            user = User.objects.get(id=user_id)
            
            if default_token_generator.check_token(user, token):
                user.is_active = True
                user.save()
                
                return Response({'message': 'Email успешно подтвержден'})
            else:
                return Response(
                    {'error': 'Неверный токен'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except User.DoesNotExist:
            return Response(
                {'error': 'Пользователь не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def forgot_password(self, request):
        """
        Запрос восстановления пароля
        POST /api/auth/forgot-password/
        """
        email = request.data.get('email')
        
        try:
            user = User.objects.get(email__iexact=email)
            
            # ✅ Генерируем токен сброса пароля
            token = default_token_generator.make_token(user)
            
            # Отправляем email с ссылкой сброса
            reset_link = f"{settings.FRONTEND_URL}/reset-password?user_id={user.id}&token={token}"
            
            send_mail(
                subject="Восстановление пароля FREESPORT",
                message=f"Ссылка для сброса пароля: {reset_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
            
            return Response({'message': 'Инструкция отправлена на email'})
            
        except User.DoesNotExist:
            # ✅ Безопасность: не раскрываем существование email
            return Response({'message': 'Если email существует, инструкция отправлена'})
    
    def send_verification_email(self, user):
        """Отправка email подтверждения"""
        token = default_token_generator.make_token(user)
        verification_link = f"{settings.FRONTEND_URL}/verify-email?user_id={user.id}&token={token}"
        
        send_mail(
            subject="Подтверждение регистрации FREESPORT",
            message=f"Ссылка для подтверждения: {verification_link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """Кастомный view для получения JWT токена"""
    serializer_class = CustomTokenObtainPairSerializer
```

## Frontend интеграция

### React Auth Hook

```typescript
interface User {
  id: number;
  email: string;
  role: string;
  full_name: string;
  is_verified: boolean;
}

interface AuthState {
  user: User | null;
  access_token: string | null;
  refresh_token: string | null;
  loading: boolean;
}

const useAuth = () => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    access_token: localStorage.getItem('access_token'),
    refresh_token: localStorage.getItem('refresh_token'),
    loading: false,
  });

  const login = async (email: string, password: string) => {
    setAuthState(prev => ({ ...prev, loading: true }));
    
    try {
      const response = await fetch('/api/auth/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        // ✅ Сохраняем токены и пользователя
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        
        setAuthState({
          user: data.user,
          access_token: data.access,
          refresh_token: data.refresh,
          loading: false,
        });
        
        return { success: true };
      } else {
        return { success: false, errors: data };
      }
    } catch (error) {
      return { success: false, errors: { non_field_errors: ['Ошибка сети'] } };
    } finally {
      setAuthState(prev => ({ ...prev, loading: false }));
    }
  };

  const register = async (userData: RegisterData) => {
    setAuthState(prev => ({ ...prev, loading: true }));
    
    try {
      const response = await fetch('/api/auth/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
      });
      
      const data = await response.json();
      
      return { success: response.ok, data, errors: response.ok ? null : data };
    } finally {
      setAuthState(prev => ({ ...prev, loading: false }));
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setAuthState({
      user: null,
      access_token: null,
      refresh_token: null,
      loading: false,
    });
  };

  return { ...authState, login, register, logout };
};
```

## Миграция данных

### Создание суперпользователя

```python
# management/commands/create_superuser.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Создание суперпользователя с email аутентификацией'
    
    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='Email суперпользователя')
        parser.add_argument('--password', required=True, help='Пароль')
    
    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f'Пользователь с email {email} уже существует')
            )
            return
        
        User.objects.create_superuser(
            email=email,
            password=password,
            first_name='Admin',
            last_name='User'
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Суперпользователь {email} успешно создан')
        )
```

## Тестирование

```python
class TestCustomUserModel:
    
    @pytest.mark.unit
    def test_create_user_with_email(self):
        """Создание пользователя с email"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='retail'
        )
        
        assert user.email == 'test@example.com'
        assert user.role == 'retail'
        assert user.check_password('testpass123')
        assert user.username is None  # username отключен

    @pytest.mark.unit
    def test_email_normalization(self):
        """Нормализация email при создании"""
        user = User.objects.create_user(
            email='Test@EXAMPLE.com',
            password='testpass123'
        )
        
        assert user.email == 'Test@example.com'  # Домен в lowercase

    @pytest.mark.integration
    def test_login_with_email(self, api_client):
        """Тест входа через email"""
        user = UserFactory(email='test@example.com')
        user.set_password('testpass123')
        user.save()
        
        response = api_client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        
        assert response.status_code == 200
        data = response.json()
        assert 'access' in data
        assert 'refresh' in data
        assert data['user']['email'] == 'test@example.com'
```

Этот паттерн обеспечивает современную email-аутентификацию с поддержкой ролевой системы B2B/B2C!