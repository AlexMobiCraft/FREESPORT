"""
Views для статических страниц
"""

from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .cache_keys import PAGES_LIST_CACHE_KEY, PAGES_LIST_CACHE_TTL
from .models import Page
from .serializers import PageSerializer


class PagesPagination(PageNumberPagination):
    """Пагинация списка страниц с поддержкой `?page_size`.

    Глобальный `PAGE_SIZE_QUERY_PARAM` в DRF не действует — это атрибут класса
    пагинации, а не настройка (как в `apps.bonuses.views`, `apps.products.views`).
    Без этого класса `?page_size=1000` молча игнорируется, выдача обрезается до
    `PAGE_SIZE` = 20, и middleware фронтенда видит лишь первые 20 CMS-слагов:
    21-я и далее опубликованные страницы начали бы отдавать 404.
    """

    page_size_query_param = "page_size"
    max_page_size = 1000


class PageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для чтения статических страниц"""

    serializer_class = PageSerializer
    lookup_field = "slug"
    permission_classes = [permissions.AllowAny]
    pagination_class = PagesPagination

    def get_queryset(self):
        """Получить только опубликованные страницы"""
        return Page.objects.filter(is_published=True)

    @extend_schema(
        summary="Получить список страниц",
        description="Возвращает список всех опубликованных статических страниц",
        tags=["Pages"],
    )
    def list(self, request, *args, **kwargs):
        """Получить список страниц с кэшированием.

        Кэшируется ПОЛНЫЙ сериализованный список опубликованных страниц, а
        пагинация применяется к нему уже на каждом запросе. Раньше кэшировался
        готовый ответ под одним ключом `pages_list` независимо от параметров:
        клиент, запросивший `?page_size=1000`, получал закэшированную первую
        страницу из 20 записей (`PAGE_SIZE` DRF). Для middleware фронтенда,
        который по этому списку решает, отдавать ли настоящий 404, это означало
        молчаливый 404 на 21-й и далее CMS-странице.

        Один ключ на всю выдачу выбран намеренно: он не даёт размножать записи
        кэша произвольными значениями `page_size` и оставляет инвалидацию
        точечной — сигнал удаляет ровно один ключ (`signals.invalidate_page_cache`).
        """
        serialized_pages = cache.get(PAGES_LIST_CACHE_KEY)

        if serialized_pages is None:
            queryset = self.filter_queryset(self.get_queryset())
            serialized_pages = list(self.get_serializer(queryset, many=True).data)
            cache.set(PAGES_LIST_CACHE_KEY, serialized_pages, PAGES_LIST_CACHE_TTL)

        page = self.paginate_queryset(serialized_pages)
        if page is not None:
            return self.get_paginated_response(page)

        return Response(serialized_pages)

    @extend_schema(
        summary="Получить страницу по slug",
        description="Возвращает содержимое статической страницы по URL slug",
        tags=["Pages"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Получить страницу с кэшированием по предсказуемому ключу"""
        slug = kwargs.get(self.lookup_field)
        cache_key = f"page_detail_{slug}"
        cached = cache.get(cache_key)

        if cached is not None:
            return Response(cached)

        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, 60 * 60 * 24)
        return response
