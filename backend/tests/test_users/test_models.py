"""
Тесты для моделей пользователей FREESPORT Platform
"""
import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model, authenticate
from django.db import IntegrityError

from tests.factories import UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """
    Тесты модели пользователя User
    """

    def test_user_creation_with_valid_data(self):
        """
        Тест создания пользователя с валидными данными
        """
        user = UserFactory.create(
            email='test@freesport.com',
            first_name='Иван',
            last_name='Петров',
            role='retail'
        )
        
        assert user.email == 'test@freesport.com'
        assert user.first_name == 'Иван'
        assert user.last_name == 'Петров'
        assert user.role == 'retail'
        assert user.is_active is True
        assert user.is_verified is False  # По умолчанию не верифицирован
        assert user.username is None  # Используем email для авторизации

    def test_user_str_representation(self):
        """
        Тест строкового представления пользователя
        """
        user = UserFactory.create(
            email='test@freesport.com',
            role='wholesale_level1'
        )
        representation = str(user)
        
        # Более гибкая проверка содержания ключевых частей
        assert user.email in representation
        assert user.get_role_display() in representation

    def test_user_full_name_property(self):
        """
        Тест свойства full_name
        """
        user = UserFactory.create(
            first_name='Иван',
            last_name='Петров'
        )
        assert user.full_name == 'Иван Петров'

        # Тест с пустыми полями
        user_empty = UserFactory.create(first_name='', last_name='')
        assert user_empty.full_name == ''

        # Тест с одним заполненным полем
        user_partial = UserFactory.create(first_name='Иван', last_name='')
        assert user_partial.full_name == 'Иван'

    def test_unique_email_constraint(self):
        """
        Тест уникальности email
        """
        email = 'duplicate@freesport.com'
        UserFactory.create(email=email)
        
        with pytest.raises(IntegrityError):
            UserFactory.create(email=email)

    def test_valid_phone_number(self):
        """
        Тест валидного номера телефона
        """
        user = UserFactory.build(phone='+79001234567')
        # Проверяем что валидация проходит
        user.full_clean()  # Вызывает валидацию модели
        user.save()
        assert user.phone == '+79001234567'

    @pytest.mark.parametrize(
        "invalid_phone",
        [
            '89001234567',  # Без +7
            '+7900123456',  # Короткий номер
            '+790012345678',  # Длинный номер
            'invalid_phone',  # Нечисловой
        ]
    )
    def test_invalid_phone_number(self, invalid_phone):
        """
        Тест невалидного номера телефона
        """
        with pytest.raises(ValidationError):
            user = UserFactory.build(phone=invalid_phone)
            user.full_clean()

    @pytest.mark.parametrize(
        "role, expected_is_b2b",
        [
            # B2B роли
            ('wholesale_level1', True),
            ('wholesale_level2', True),
            ('wholesale_level3', True),
            ('trainer', True),
            ('federation_rep', True),
            # B2C роли
            ('retail', False),
            ('admin', False),
        ]
    )
    def test_is_b2b_user_property(self, role, expected_is_b2b):
        """
        Тест свойства is_b2b_user для разных ролей
        """
        user = UserFactory.create(role=role)
        assert user.is_b2b_user is expected_is_b2b

    @pytest.mark.parametrize(
        "role, expected_is_wholesale",
        [
            # Оптовые роли
            ('wholesale_level1', True),
            ('wholesale_level2', True),
            ('wholesale_level3', True),
            # Не оптовые роли
            ('retail', False),
            ('trainer', False),
            ('federation_rep', False),
            ('admin', False),
        ]
    )
    def test_is_wholesale_user_property(self, role, expected_is_wholesale):
        """
        Тест свойства is_wholesale_user для разных ролей
        """
        user = UserFactory.create(role=role)
        assert user.is_wholesale_user is expected_is_wholesale

    @pytest.mark.parametrize(
        "role, expected_level",
        [
            # Оптовые пользователи разных уровней
            ('wholesale_level1', 1),
            ('wholesale_level2', 2),
            ('wholesale_level3', 3),
            # Не оптовые пользователи
            ('retail', None),
            ('trainer', None),
            ('federation_rep', None),
            ('admin', None),
        ]
    )
    def test_wholesale_level_property(self, role, expected_level):
        """
        Тест свойства wholesale_level для разных ролей
        """
        user = UserFactory.create(role=role)
        assert user.wholesale_level == expected_level

    @pytest.mark.parametrize(
        "valid_role",
        [
            'retail',
            'wholesale_level1',
            'wholesale_level2', 
            'wholesale_level3',
            'trainer',
            'federation_rep',
            'admin'
        ]
    )
    def test_valid_role_choices(self, valid_role):
        """
        Тест валидных ролей
        """
        user = UserFactory.build(role=valid_role)
        user.full_clean()  # Не должно вызывать исключение
        assert user.role == valid_role

    def test_invalid_role_choice(self):
        """
        Тест невалидной роли
        """
        with pytest.raises(ValidationError):
            user = UserFactory.build(role='invalid_role')
            user.full_clean()

    def test_b2b_fields_for_business_users(self):
        """
        Тест B2B полей для бизнес пользователей
        """
        b2b_user = UserFactory.create(
            role='wholesale_level1',
            company_name='ООО Спорт Компани',
            tax_id='7701234567890',
            is_verified=True
        )
        
        assert b2b_user.company_name == 'ООО Спорт Компани'
        assert b2b_user.tax_id == '7701234567890'
        assert b2b_user.is_verified is True
        assert b2b_user.is_b2b_user is True

    def test_default_values(self):
        """
        Тест значений по умолчанию
        """
        user = UserFactory.create()
        
        assert user.role == 'retail'
        assert user.is_active is True
        assert user.is_verified is False
        assert user.phone == ''
        assert user.company_name == ''
        assert user.tax_id == ''

    def test_username_field_configuration(self):
        """
        Тест настройки USERNAME_FIELD
        """
        assert User.USERNAME_FIELD == 'email'
        assert 'first_name' in User.REQUIRED_FIELDS
        assert 'last_name' in User.REQUIRED_FIELDS

    def test_meta_configuration(self):
        """
        Тест настроек Meta класса
        """
        assert User._meta.verbose_name == 'Пользователь'
        assert User._meta.verbose_name_plural == 'Пользователи'
        assert User._meta.db_table == 'users'

    def test_user_authentication_with_email(self):
        """
        Тест аутентификации пользователя через email
        """
        # Фабрика автоматически хеширует пароль через PostGenerationMethodCall
        user = UserFactory.create(
            email='auth@freesport.com',
            password='test_password123'
        )
        
        authenticated_user = authenticate(
            username='auth@freesport.com',  # USERNAME_FIELD = email
            password='test_password123'
        )
        
        assert authenticated_user is not None
        assert authenticated_user == user