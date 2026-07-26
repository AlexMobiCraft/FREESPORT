# Перевод импортированных из 1С контрагентов из retail в unregistered.
#
# До этой миграции импорт присваивал всем контрагентам role='retail'
# (ROLE_MAPPING ждал названия типов цен "Опт 1"/"Тренерская"/"РРЦ", а парсер
# отдавал customer_type "legal_entity"/"individual_entrepreneur"/"individual",
# поэтому всегда срабатывал fallback). Из-за этого ветка привязки регистрации
# к записи 1С, требующая role != "retail", не выполнялась никогда.

import logging

from django.db import migrations, models

logger = logging.getLogger(__name__)


def _target_queryset(user_model):
    """
    Записи 1С без портального аккаунта.

    Пустой password — надёжный отличительный признак: контрагент из 1С
    создаётся через User.objects.create() без пароля и войти не может,
    тогда как у любого портального аккаунта пароль захеширован.
    """
    return user_model.objects.filter(
        created_in_1c=True,
        verification_status="unverified",
    ).filter(models.Q(password="") | models.Q(password__isnull=True))


def set_unregistered_role(apps, schema_editor):
    """retail → unregistered для контрагентов 1С без пароля."""
    User = apps.get_model("users", "User")

    updated = _target_queryset(User).filter(role="retail").update(role="unregistered")

    logger.info("Переведено в role='unregistered': %s записей 1С", updated)


def restore_retail_role(apps, schema_editor):
    """
    unregistered → retail.

    Роль unregistered назначается только импортом 1С, поэтому обратный
    переход безопасно применять ко всем записям с этой ролью.
    """
    User = apps.get_model("users", "User")

    restored = User.objects.filter(role="unregistered").update(role="retail")

    logger.info("Возвращено в role='retail': %s записей", restored)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0017_add_unregistered_role"),
    ]

    operations = [
        migrations.RunPython(set_unregistered_role, restore_retail_role),
    ]
