"""
Тесты для User Serializers - Story 2.2 User Management API
"""
import pytest
from django.contrib.auth import get_user_model

from apps.users.serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserDashboardSerializer,
    AddressSerializer,
    FavoriteSerializer,
)

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistrationSerializer:
    """Тесты сериализатора регистрации пользователей"""

    def test_valid_retail_user_registration(self, user_factory):
        """Тест создания retail пользователя"""
        data = {
            'email': 'test@test.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': 'Тест',
            'last_name': 'Пользователь',
            'phone': '+79991234568',
            'role': 'retail'
        }

        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        user = serializer.save()
        assert user.email == 'test@test.com'
        assert user.role == 'retail'
        assert user.is_active is True

    def test_valid_b2b_user_registration(self, user_factory):
        """Тест создания B2B пользователя"""
        data = {
            'email': 'b2b@test.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': 'B2B',
            'last_name': 'Пользователь',
            'phone': '+79991234567',
            'role': 'wholesale_level1',
            'company_name': 'Тест Компания',
            'tax_id': '1234567890'
        }

        serializer = UserRegistrationSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        user = serializer.save()
        assert user.email == 'b2b@test.com'
        assert user.role == 'wholesale_level1'
        assert user.company_name == 'Тест Компания'

    def test_password_mismatch(self, user_factory):
        """Тест несовпадения паролей"""
        data = {
            'email': 'test@test.com',
            'password': 'TestPass123!',
            'password_confirm': 'DifferentPass123!',
            'first_name': 'Тест',
            'last_name': 'Пользователь',
            'phone': '+79991234568',
            'role': 'retail'
        }

        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password_confirm' in serializer.errors

    def test_duplicate_email(self, user_factory):
        """Тест дублирования email"""
        user_factory.create(email='existing@test.com')

        data = {
            'email': 'existing@test.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': 'Тест',
            'last_name': 'Пользователь',
            'phone': '+79991234568',
            'role': 'retail'
        }

        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'email' in serializer.errors

    def test_b2b_missing_company_data(self, user_factory):
        """Тест B2B регистрации без данных компании"""
        data = {
            'email': 'b2b@test.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': 'B2B',
            'last_name': 'Пользователь',
            'phone': '+79991234568',
            'role': 'wholesale_level1'
        }

        serializer = UserRegistrationSerializer(data=data)
        assert not serializer.is_valid()
        assert 'company_name' in serializer.errors


@pytest.mark.django_db
class TestUserLoginSerializer:
    """Тесты сериализатора входа пользователя"""

    def test_valid_login(self, user_factory):
        """Тест успешного входа"""
        user = user_factory.create(
            email='test@test.com',
            password='testpass123'
        )

        data = {
            'email': 'test@test.com',
            'password': 'testpass123'
        }

        serializer = UserLoginSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        validated_data = serializer.validated_data
        assert validated_data['user'] == user

    def test_invalid_email(self, user_factory):
        """Тест неверного email"""
        data = {
            'email': 'nonexistent@test.com',
            'password': 'testpass123'
        }

        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_invalid_password(self, user_factory):
        """Тест неверного пароля"""
        user_factory.create(
            email='test@test.com',
            password='correctpass'
        )

        data = {
            'email': 'test@test.com',
            'password': 'wrongpass'
        }

        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_inactive_user_login(self, user_factory):
        """Тест входа неактивного пользователя"""
        user_factory.create(
            email='inactive@test.com',
            password='testpass123',
            is_active=False
        )

        data = {
            'email': 'inactive@test.com',
            'password': 'testpass123'
        }

        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors


@pytest.mark.django_db
class TestUserProfileSerializer:
    """Тесты сериализатора профиля пользователя"""

    def test_profile_serialization(self, user_factory):
        """Тест сериализации профиля пользователя"""
        user = user_factory.create(
            email='test@test.com',
            first_name='Тест',
            last_name='Пользователь',
            phone='+7999123456'
        )

        serializer = UserProfileSerializer(user)
        data = serializer.data

        assert data['email'] == 'test@test.com'
        assert data['first_name'] == 'Тест'
        assert data['last_name'] == 'Пользователь'
        assert data['phone'] == '+7999123456'

    def test_profile_update(self, user_factory):
        """Тест обновления профиля"""
        user = user_factory.create(
            email='test@test.com',
            first_name='Старое',
            last_name='Имя'
        )

        data = {
            'first_name': 'Новое',
            'last_name': 'Имя',
            'phone': '+79996543210'
        }

        serializer = UserProfileSerializer(user, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors

        updated_user = serializer.save()
        assert updated_user.first_name == 'Новое'
        assert updated_user.last_name == 'Имя'
        assert updated_user.phone == '+79996543210'

    def test_email_update_not_allowed(self, user_factory):
        """Тест что email нельзя изменить через профиль"""
        user = user_factory.create(email='original@test.com')

        data = {'email': 'new@test.com'}

        serializer = UserProfileSerializer(user, data=data, partial=True)
        assert serializer.is_valid()

        updated_user = serializer.save()
        assert updated_user.email == 'original@test.com'


@pytest.mark.django_db
class TestAddressSerializer:
    """Тесты сериализатора адресов"""

    def test_address_creation(self, user_factory, address_factory):
        """Тест создания адреса"""
        user = user_factory.create()

        data = {
            'user': user.id,
            'address_type': 'shipping',
            'full_name': 'Иван Петров',
            'phone': '+79001234567',
            'city': 'Москва',
            'street': 'Тверская',
            'building': '1',
            'apartment': '10',
            'postal_code': '101000',
            'is_default': True
        }

        serializer = AddressSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        address = serializer.save()
        assert address.city == 'Москва'
        assert address.is_default is True

    def test_address_validation(self, user_factory):
        """Тест валидации адреса"""
        user = user_factory.create()

        data = {
            'user': user.id,
            'address_type': 'invalid_type',
            'city': 'Москва'
        }

        serializer = AddressSerializer(data=data)
        assert not serializer.is_valid()
        expected_errors = ['full_name', 'phone', 'street', 'building', 'postal_code']
        for field in expected_errors:
            assert field in serializer.errors


@pytest.mark.django_db
class TestFavoriteSerializer:
    """Тесты сериализатора избранного"""

    def test_favorite_serialization(self, user_factory, product_factory):
        """Тест сериализации избранного товара"""
        user = user_factory.create()
        product = product_factory.create(name='Тестовый товар')

        favorite_data = {
            'user': user,
            'product': product
        }

        # Создаем объект избранного напрямую для тестирования сериализации
        from apps.users.models import Favorite
        favorite = Favorite.objects.create(**favorite_data)

        serializer = FavoriteSerializer(favorite)
        data = serializer.data

        assert 'product' in data
        assert 'created_at' in data

    def test_favorite_creation_validation(self, user_factory, product_factory):
        """Тест валидации создания избранного"""
        user = user_factory.create()
        product = product_factory.create()

        data = {
            'product': product.id
        }

        # Передаем context с user для корректного создания
        serializer = FavoriteSerializer(data=data, context={'request': type('obj', (object,), {'user': user})()})
        assert serializer.is_valid(), serializer.errors

        favorite = serializer.save(user=user)
        assert favorite.user == user
        assert favorite.product == product


@pytest.mark.django_db
class TestUserDashboardSerializer:
    """Тесты сериализатора дашборда пользователя"""

    def test_dashboard_data(self, user_factory):
        """Тест данных дашборда"""
        user = user_factory.create(role='retail')

        # Создаем объект с правильной структурой для UserDashboardSerializer
        class DashboardData:
            def __init__(self, user):
                self.user_info = user
                self.orders_count = 5
                self.favorites_count = 10
                self.addresses_count = 2
                self.total_order_amount = 50000.00

        dashboard_data = DashboardData(user)
        serializer = UserDashboardSerializer(dashboard_data)
        data = serializer.data

        assert 'orders_count' in data
        assert 'favorites_count' in data
        assert 'addresses_count' in data
        assert data['orders_count'] == 5
        assert data['favorites_count'] == 10
