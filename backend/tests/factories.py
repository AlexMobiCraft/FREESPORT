"""
Factory Boy фабрики для создания тестовых объектов FREESPORT Platform
"""
import factory
from django.contrib.auth import get_user_model

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
    
    # Правильная настройка пароля с автоматическим хешированием
    password = factory.PostGenerationMethodCall('set_password', 'default_password123')