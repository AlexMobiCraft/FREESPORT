from __future__ import annotations

from django import forms

from .models import Brand


class MergeBrandsActionForm(forms.Form):
    """Форма выбора целевого бренда для объединения"""

    target_brand = forms.ModelChoiceField(
        queryset=Brand.objects.all().order_by("name"),
        label="Целевой бренд",
        help_text="Выберите бренд, в который будут объединены выбранные бренды. Исходные бренды будут удалены.",
        required=True,
    )


class TransferMappingsActionForm(forms.Form):
    """Форма выбора целевого бренда для переноса маппингов"""

    target_brand = forms.ModelChoiceField(
        queryset=Brand.objects.all().order_by("name"),
        label="Целевой бренд",
        help_text="Выберите бренд, к которому будут привязаны выбранные маппинги.",
        required=True,
    )
