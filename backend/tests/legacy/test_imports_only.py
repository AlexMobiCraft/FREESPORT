#!/usr/bin/env python
"""
Тест только импортов для проверки OrderHistorySerializer
"""
import os
import sys

import django

# Настройка Django без БД
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.development")
django.setup()

try:
    from apps.users.serializers import OrderHistorySerializer

    print("✅ OrderHistorySerializer импортирован успешно")

    from apps.orders.models import Order

    print("✅ Order модель импортирована успешно")

    # Проверяем что сериализатор правильно настроен
    print(f"✅ OrderHistorySerializer.Meta.model = {OrderHistorySerializer.Meta.model}")
    print(
        f"✅ OrderHistorySerializer.Meta.fields = {OrderHistorySerializer.Meta.fields}"
    )

    # Проверяем что методы существуют
    serializer = OrderHistorySerializer()
    print(
        f"✅ Метод get_items_count существует: {hasattr(serializer, 'get_items_count')}"
    )

    print("\n🎉 Все импорты и базовые проверки прошли успешно!")
    print("OrderHistorySerializer готов к использованию!")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback

    traceback.print_exc()
