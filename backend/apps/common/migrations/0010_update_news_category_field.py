"""Миграция: Обновление поля category в модели News для связи с моделью Category.

Обновляет CharField на ForeignKey и добавляет соответствующие ограничения.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Миграция для обновления поля category в модели News."""

    dependencies = [
        ("common", "0009_add_newsletter_and_news_models"),
    ]

    operations = [
        migrations.AlterField(
            model_name="news",
            name="category",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="news",
                to="common.category",
                verbose_name="Категория",
            ),
        ),
    ]