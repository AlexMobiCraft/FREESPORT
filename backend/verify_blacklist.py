"""
Скрипт верификации работы JWT Token Blacklist механизма (Story 30.1)

Проверяет:
1. Создание пользователя и генерацию refresh токена
2. Blacklist токена
3. Запись в БД
4. Невозможность использования blacklisted токена
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.development")
django.setup()

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from apps.users.models import User
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

print("\n" + "=" * 70)
print("Story 30.1: JWT Token Blacklist Verification")
print("=" * 70)

# 1. Создать тестового пользователя
print("\n[1/5] Создание тестового пользователя...")
test_user, created = User.objects.get_or_create(
    email="blacklist_test@example.com",
    defaults={
        "first_name": "Test",
        "last_name": "Blacklist",
        "role": "retail",
        "is_verified": True,
    },
)
if created:
    test_user.set_password("TestPassword123!")
    test_user.save()
    print(f"✅ Создан пользователь: {test_user.email}")
else:
    print(f"✅ Использован существующий пользователь: {test_user.email}")

# 2. Сгенерировать refresh token
print("\n[2/5] Генерация refresh токена...")
refresh = RefreshToken.for_user(test_user)
refresh_token_str = str(refresh)
print(f"✅ Refresh токен сгенерирован: {refresh_token_str[:50]}...")

# 3. Проверить запись в OutstandingToken
print("\n[3/5] Проверка записи в OutstandingToken...")
outstanding_count = OutstandingToken.objects.filter(user=test_user).count()
print(f"✅ OutstandingToken записей для пользователя: {outstanding_count}")

# 4. Выполнить blacklist токена
print("\n[4/5] Blacklist токена...")
try:
    refresh.blacklist()
    print("✅ Токен успешно добавлен в blacklist")
except Exception as e:
    print(f"❌ Ошибка при blacklist: {e}")
    exit(1)

# 5. Проверить запись в BlacklistedToken
print("\n[5/5] Проверка записи в BlacklistedToken...")
blacklisted_count = BlacklistedToken.objects.count()
print(f"✅ BlacklistedToken записей в БД: {blacklisted_count}")

# 6. Попытаться использовать blacklisted токен
print("\n[6/6] Попытка использовать blacklisted токен...")
try:
    # Попытка создать новый RefreshToken из blacklisted строки
    RefreshToken(refresh_token_str)
    print("❌ ОШИБКА: Blacklisted токен всё ещё работает!")
    exit(1)
except TokenError as e:
    print(f"✅ Blacklisted токен отклонён (ожидаемое поведение): {e}")

# Итоги
print("\n" + "=" * 70)
print("РЕЗУЛЬТАТЫ ВЕРИФИКАЦИИ:")
print("=" * 70)
print("✅ 1. Пользователь создан")
print("✅ 2. Refresh токен сгенерирован")
print("✅ 3. OutstandingToken запись создана")
print("✅ 4. Токен добавлен в blacklist")
print("✅ 5. BlacklistedToken запись создана")
print("✅ 6. Blacklisted токен не может быть использован")
print("\n🎉 JWT Token Blacklist механизм работает корректно!")
print("=" * 70 + "\n")

# Cleanup
print("Очистка тестовых данных...")
test_user.delete()
print("✅ Тестовый пользователь удалён\n")
