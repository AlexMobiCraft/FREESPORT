"""
Тесты для моделей пользователей FREESPORT Platform
"""
import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model, authenticate
from django.db import IntegrityError
from django.contrib.auth.management.commands import createsuperuser
from django.core.management import CommandError
from io import StringIO
import uuid
import time

from tests.conftest import UserFactory, CompanyFactory, AddressFactory


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
            email="test@freesport.com",
            first_name="Иван",
            last_name="Петров",
            role="retail",
        )

        assert user.email == "test@freesport.com"
        assert user.first_name == "Иван"
        assert user.last_name == "Петров"
        assert user.role == "retail"
        assert user.is_active is True
        assert user.is_verified is False  # По умолчанию не верифицирован
        assert (
            hasattr(user, "username") is False or user.username is None
        )  # Используем email для авторизации

    def test_user_str_representation(self):
        """
        Тест строкового представления пользователя
        """
        user = UserFactory.create(email="test@freesport.com", role="wholesale_level1")
        representation = str(user)

        # Более гибкая проверка содержания ключевых частей
        assert user.email in representation
        assert user.get_role_display() in representation

    def test_user_full_name_property(self):
        """
        Тест свойства full_name
        """
        user = UserFactory.create(first_name="Иван", last_name="Петров")
        assert user.full_name == "Иван Петров"

        # Тест с пустыми полями
        user_empty = UserFactory.create(first_name="", last_name="")
        assert user_empty.full_name == ""

        # Тест с одним заполненным полем
        user_partial = UserFactory.create(first_name="Иван", last_name="")
        assert user_partial.full_name == "Иван"

    def test_unique_email_constraint(self):
        """
        Тест уникальности email
        """
        email = f'duplicate-test-{int(time.time())}-{uuid.uuid4().hex[:8]}@freesport.com'
        UserFactory.create(email=email)

        with pytest.raises(IntegrityError):
            UserFactory.create(email=email)

    def test_valid_phone_number(self):
        """
        Тест валидного номера телефона
        """
        user = UserFactory.build(phone="+79001234567")
        # Проверяем что валидация проходит
        user.full_clean()  # Вызывает валидацию модели
        user.save()
        assert user.phone == "+79001234567"

    @pytest.mark.parametrize(
        "invalid_phone",
        [
            "89001234567",  # Без +7
            "+7900123456",  # Короткий номер
            "+790012345678",  # Длинный номер
            "invalid_phone",  # Нечисловой
        ],
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
            ("wholesale_level1", True),
            ("wholesale_level2", True),
            ("wholesale_level3", True),
            ("trainer", True),
            ("federation_rep", True),
            # B2C роли
            ("retail", False),
            ("admin", False),
        ],
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
            ("wholesale_level1", True),
            ("wholesale_level2", True),
            ("wholesale_level3", True),
            # Не оптовые роли
            ("retail", False),
            ("trainer", False),
            ("federation_rep", False),
            ("admin", False),
        ],
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
            ("wholesale_level1", 1),
            ("wholesale_level2", 2),
            ("wholesale_level3", 3),
            # Не оптовые пользователи
            ("retail", None),
            ("trainer", None),
            ("federation_rep", None),
            ("admin", None),
        ],
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
            "retail",
            "wholesale_level1",
            "wholesale_level2",
            "wholesale_level3",
            "trainer",
            "federation_rep",
            "admin",
        ],
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
            user = UserFactory.build(role="invalid_role")
            user.full_clean()

    def test_b2b_fields_for_business_users(self):
        """
        Тест B2B полей для бизнес пользователей
        """
        b2b_user = UserFactory.create(
            company_name='ООО Спорт Компани',
            tax_id='770123456789',
            is_verified=True
        )
        
        assert b2b_user.company_name == 'ООО Спорт Компани'
        assert b2b_user.tax_id == '770123456789'
            company_name="ООО Спорт Компани",
            tax_id="7701234567890",
            is_verified=True,
        )

        assert b2b_user.company_name == "ООО Спорт Компани"
        assert b2b_user.tax_id == "7701234567890"
        assert b2b_user.is_b2b_user is True

    def test_default_values(self):
        """
        Тест значений по умолчанию
        """
        
        assert user.role == 'retail'

        assert user.role == "retail"
        assert user.is_verified is False
        assert user.phone == ""
        assert user.company_name == ""
        assert user.tax_id == ""

    def test_username_field_configuration(self):
        """
        Тест настройки USERNAME_FIELD
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()
        assert User.USERNAME_FIELD == "email"
        assert "first_name" in User.REQUIRED_FIELDS
        assert "last_name" in User.REQUIRED_FIELDS

    def test_meta_configuration(self):
        """
        Тест настроек Meta класса
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()
        assert User._meta.verbose_name == "Пользователь"
        assert User._meta.verbose_name_plural == "Пользователи"
        assert User._meta.db_table == "users"

    def test_user_authentication_with_email(self):
        """
        Тест аутентификации пользователя через email
        """
        # Фабрика автоматически хеширует пароль через PostGenerationMethodCall
        user = UserFactory.create(
            email="auth@freesport.com", password="test_password123"
        )

        authenticated_user = authenticate(
            username="auth@freesport.com",  # USERNAME_FIELD = email
            password="test_password123",
        )

        assert authenticated_user is not None
        assert authenticated_user == user

    def test_createsuperuser_without_required_fields_fails(self):
        """
        Тест: создание суперпользователя без обязательных полей должно вызывать ошибку
        """
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with pytest.raises((CommandError, SystemExit)):
            call_command(
                "createsuperuser",
                email="admin@test.com",
                interactive=False,
                verbosity=0,
            )

    def test_b2c_user_can_have_empty_b2b_fields(self):
        """
        Тест: B2C пользователь может иметь пустые B2B поля без ошибок
        """
        retail_user = UserFactory.create(
            role="retail",
            company_name="",  # Пустое, но не должно вызывать ошибку
            tax_id="",
            is_verified=False,
        )

        retail_user.full_clean()  # Не должно вызывать ValidationError
        assert retail_user.role == "retail"
        assert retail_user.company_name == ""
        assert retail_user.tax_id == ""
        assert retail_user.is_b2b_user is False


@pytest.mark.django_db
class TestCompanyModel:
    """
    Тесты модели компании Company
    """

    def test_company_creation(self):
        """
        Тест успешного создания компании
        """
        user = UserFactory.create(role="wholesale_level1", is_verified=True)
        company = CompanyFactory.create(
            user=user, legal_name='ООО "Рога и Копыта"', tax_id="123456789012"
        )

        assert company.user == user
        assert company.legal_name == 'ООО "Рога и Копыта"'
        assert company.tax_id == "123456789012"
        assert str(company) == 'ООО "Рога и Копыта" (ИНН: 123456789012)'

    def test_tax_id_uniqueness(self):
        """
        Тест: ИНН компании должен быть уникальным
        """
        user2 = UserFactory.create(role='wholesale_level2')
        
        test_tax_id = f'{111222333000 + int(time.time()) % 999:012d}'
        CompanyFactory.create(user=user1, tax_id=test_tax_id)
        
        with pytest.raises(IntegrityError):
            CompanyFactory.create(user=user2, tax_id=test_tax_id)
        user2 = UserFactory.create(role="wholesale_level2")

        CompanyFactory.create(user=user1, tax_id="111222333444")

        with pytest.raises(IntegrityError):
            CompanyFactory.create(user=user2, tax_id="111222333444")
    def test_one_to_one_relationship_with_user(self):
        """
        Тест связи OneToOne с пользователем
        """
        user = UserFactory.create(role="wholesale_level1")
        company = CompanyFactory.create(user=user)

        # Проверяем прямую связь
        assert company.user == user
        # Проверяем обратную связь
        assert user.company == company

        # Попытка создать вторую компанию для того же пользователя должна вызвать ошибку
        with pytest.raises(IntegrityError):
            CompanyFactory.create(user=user)

    def test_company_fields_validation(self):
        """
        Тест валидации полей компании
        """
        user = UserFactory.create(role="wholesale_level1")
        company = CompanyFactory.build(
            user=user,
            legal_name="ИП Иванов Иван Иванович",
            tax_id="123456789012",
            kpp="123456789",
            legal_address="г. Москва, ул. Тверская, д. 1",
        )

        company.full_clean()  # Не должно вызывать ValidationError
        assert company.legal_name == "ИП Иванов Иван Иванович"
        assert len(company.tax_id) == 12
        assert len(company.kpp) == 9

    def test_company_meta_configuration(self):
        """
        Тест настроек Meta класса Company
        """
        from apps.users.models import Company

        assert Company._meta.verbose_name == "Компания"
        assert Company._meta.verbose_name_plural == "Компании"
        assert Company._meta.db_table == "companies"


@pytest.mark.django_db
class TestAddressModel:
    """
    Тесты модели адреса Address
    """

    def test_address_creation(self):
        """
        Тест успешного создания адреса
        """
        user = UserFactory.create()
        address = AddressFactory.create(
            user=user,
            city="Москва",
            street="Тверская",
            building="1",
            full_name="Иван Иванов",
        )

        assert address.user == user
        assert address.city == "Москва"
        assert address.street == "Тверская"
        assert address.building == "1"
        assert "Москва, Тверская 1" in str(address)

    def test_full_address_property(self):
        """
        Тест свойства полного адреса
        """
        address = AddressFactory.build(
            postal_code="123456",
            city="Москва",
            street="Тверская",
            building="1",
            apartment="101",
        )

        expected = "123456, Москва, Тверская, 1, кв. 101"
        assert address.full_address == expected

    def test_full_address_property_without_apartment(self):
        """
        Тест свойства полного адреса без квартиры
        """
        address = AddressFactory.build(
            postal_code="654321",
            city="Санкт-Петербург",
            street="Невский проспект",
            building="50",
            apartment="",
        )

        expected = "654321, Санкт-Петербург, Невский проспект, 50"
        assert address.full_address == expected

    def test_multiple_addresses_for_user(self):
        """
        Тест создания нескольких адресов для одного пользователя
        """
        user = UserFactory.create()

        shipping_address = AddressFactory.create(
            user=user, address_type="shipping", is_default=True
        )
        legal_address = AddressFactory.create(
            user=user, address_type="legal", is_default=False
        )

        assert user.addresses.count() == 2
        assert shipping_address.address_type == "shipping"
        assert legal_address.address_type == "legal"
        assert shipping_address.is_default is True
        assert legal_address.is_default is False

    def test_address_types_choices(self):
        """
        Тест валидных типов адресов
        """
        user = UserFactory.create()

        # Тест валидных типов
        shipping_address = AddressFactory.create(user=user, address_type="shipping")
        legal_address = AddressFactory.create(user=user, address_type="legal")

        shipping_address.full_clean()  # Не должно вызывать ValidationError
        legal_address.full_clean()  # Не должно вызывать ValidationError

        assert shipping_address.address_type == "shipping"
        assert legal_address.address_type == "legal"

    def test_address_str_representation(self):
        """
        Тест строкового представления адреса
        """
        address = AddressFactory.create(
            full_name="Петр Петров", city="Екатеринбург", street="Ленина", building="25"
        )

        expected = "Петр Петров - Екатеринбург, Ленина 25"
        assert str(address) == expected

    def test_address_meta_configuration(self):
        """
        Тест настроек Meta класса Address
        """
        from apps.users.models import Address

        assert Address._meta.verbose_name == "Адрес"
        assert Address._meta.verbose_name_plural == "Адреса"
        assert Address._meta.db_table == "addresses"

    def test_setting_new_default_address_unsets_old_one(self):
        """
        Тест: установка нового адреса по умолчанию снимает флаг со старого
        """
        user = UserFactory.create()

        # Создаем первый адрес как основной
        addr1 = AddressFactory.create(
            user=user, address_type="shipping", is_default=True
        )

        # Создаем второй адрес как не основной
        addr2 = AddressFactory.create(
            user=user, address_type="shipping", is_default=False
        )

        # Устанавливаем второй адрес как основной и сохраняем
        addr2.is_default = True
        addr2.save()

        # Обновляем состояние первого адреса из базы данных
        addr1.refresh_from_db()

        # Проверяем, что флаг со старого адреса снят, а у нового установлен
        assert addr1.is_default is False
        assert addr2.is_default is True
        assert (
            user.addresses.filter(address_type="shipping", is_default=True).count() == 1
        )

    def test_multiple_default_addresses_for_different_types(self):
        """
        Тест: пользователь может иметь разные адреса по умолчанию для разных типов
        """
        user = UserFactory.create()

        # Создаем основной адрес доставки
        shipping_addr = AddressFactory.create(
            user=user, address_type="shipping", is_default=True
        )

        # Создаем основной юридический адрес
        legal_addr = AddressFactory.create(
            user=user, address_type="legal", is_default=True
        )

        # Оба адреса должны остаться основными для своих типов
        assert shipping_addr.is_default is True
        assert legal_addr.is_default is True
        assert user.addresses.filter(is_default=True).count() == 2

        # Но для каждого типа должен быть только один основной
        assert (
            user.addresses.filter(address_type="shipping", is_default=True).count() == 1
        )
        assert user.addresses.filter(address_type="legal", is_default=True).count() == 1

    def test_creating_multiple_default_addresses_same_type_via_factory(self):
        """
        Тест: создание второго адреса по умолчанию через фабрику автоматически снимает флаг с первого
        """
        user = UserFactory.create()

        # Создаем первый основной адрес
        addr1 = AddressFactory.create(
            user=user, address_type="shipping", is_default=True
        )

        # Создаем второй основной адрес - должен автоматически снять флаг с первого
        addr2 = AddressFactory.create(
            user=user, address_type="shipping", is_default=True
        )

        # Обновляем первый адрес из базы
        addr1.refresh_from_db()

        # У первого адреса флаг должен быть снят
        assert addr1.is_default is False
        assert addr2.is_default is True
        assert (
            user.addresses.filter(address_type="shipping", is_default=True).count() == 1
        )

    @pytest.mark.parametrize(
        "address_type, expected_display",
        [
            ("shipping", "Адрес доставки"),
            ("legal", "Юридический адрес"),
        ],
    )
    def test_address_type_display(self, address_type, expected_display):
        """
        Тест отображения типов адресов
        """
        address = AddressFactory.create(address_type=address_type)
        assert address.get_address_type_display() == expected_display
