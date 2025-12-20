"""
Сериализаторы для API баннеров
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import serializers

from .models import Banner

if TYPE_CHECKING:
    from django.http import HttpRequest


class BannerSerializer(serializers.ModelSerializer):
    """
    Сериализатор баннера для публичного API

    Возвращает данные для отображения баннера в Hero-секции главной страницы
    """

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = [
            "id",
            "title",
            "subtitle",
            "image_url",
            "image_alt",
            "cta_text",
            "cta_link",
        ]
        read_only_fields = fields

    def get_image_url(self, obj: Banner) -> str:
        """
        Получить полный URL изображения баннера

        Args:
            obj: Объект баннера

        Returns:
            Полный URL изображения или пустая строка
        """
        request: HttpRequest | None = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return ""
