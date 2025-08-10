"""
Factory Boy фабрики для создания тестовых объектов FREESPORT Platform
"""
import factory
from django.contrib.auth import get_user_model
from apps.users.models import Company, Address

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """
    Фабрика для создания пользователей
    """
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@freesport.test")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name') 
    role = 'retail'
    is_active = True
    is_verified = False  # По умолчанию не верифицированы
    phone = ''  # По умолчанию пустой
    company_name = ''
    tax_id = ''
    
    # Правильная настройка пароля с автоматическим хешированием
    password = factory.PostGenerationMethodCall('set_password', 'default_password123')


class CompanyFactory(factory.django.DjangoModelFactory):
    """
    Фабрика для создания компаний
    """
    class Meta:
        model = Company
    
    user = factory.SubFactory(UserFactory, role='wholesale_level1', is_verified=True)
    legal_name = factory.Faker('company', locale='ru_RU')
    tax_id = factory.Sequence(lambda n: f"{1234567890 + n:012d}")  # Уникальный ИНН
    kpp = factory.Sequence(lambda n: f"{123456000 + n:09d}")
    legal_address = factory.Faker('address', locale='ru_RU')
    bank_name = factory.Faker('company', locale='ru_RU')
    bank_bik = factory.Sequence(lambda n: f"{44000000 + n:09d}")
    account_number = factory.Sequence(lambda n: f"{40702810000000000000 + n:020d}")


class AddressFactory(factory.django.DjangoModelFactory):
    """
    Фабрика для создания адресов
    """
    class Meta:
        model = Address
    
    user = factory.SubFactory(UserFactory)
    address_type = 'shipping'
    full_name = factory.LazyAttribute(lambda obj: f"{obj.user.first_name} {obj.user.last_name}")
    phone = '+79001234567'
    city = factory.Faker('city', locale='ru_RU')
    street = factory.Faker('street_name', locale='ru_RU')
    building = factory.Faker('building_number')
    apartment = factory.Faker('random_int', min=1, max=999)
    postal_code = factory.Faker('postcode', locale='ru_RU')
    is_default = False