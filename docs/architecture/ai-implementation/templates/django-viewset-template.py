"""
Шаблон Django ViewSet для FREESPORT
Скопируйте и адаптируйте под ваш API endpoint
"""
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Prefetch
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import YourModel  # TODO: Замените на вашу модель
from .serializers import (
    YourModelListSerializer,
    YourModelDetailSerializer,
    YourModelCreateSerializer,
    YourModelUpdateSerializer,
)
from .filters import YourModelFilter  # TODO: Создайте в filters.py


# ===== КАСТОМНАЯ ПАГИНАЦИЯ =====
class YourModelPagination(PageNumberPagination):
    """Кастомная пагинация для вашей модели"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# ===== ОСНОВНОЙ VIEWSET =====
class YourModelViewSet(
    viewsets.ModelViewSet
):  # TODO: Измените на ReadOnlyModelViewSet если только чтение
    """
    ViewSet для управления YourModel

    TODO: Заполните описание вашего API

    Поддерживает:
    - Список объектов с фильтрацией и поиском
    - Детальный просмотр
    - Создание (если ModelViewSet)
    - Обновление (если ModelViewSet)
    - Удаление (если ModelViewSet)
    - Кастомные действия
    """

    # ===== БАЗОВАЯ КОНФИГУРАЦИЯ =====

    # Права доступа
    permission_classes = [permissions.AllowAny]  # TODO: Настройте права доступа
    # Альтернативы:
    # permission_classes = [permissions.IsAuthenticated]
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    # permission_classes = [CustomPermission]

    # Пагинация
    pagination_class = YourModelPagination

    # Фильтрация и поиск
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]
    filterset_class = YourModelFilter
    ordering_fields = ["name", "created_at", "updated_at"]  # TODO: Добавьте нужные поля
    ordering = ["-created_at"]  # Сортировка по умолчанию
    search_fields = ["name", "description"]  # TODO: Добавьте поля для поиска

    # Lookup field (по умолчанию 'pk', но может быть 'slug' для SEO)
    lookup_field = "pk"  # TODO: Измените на 'slug' если нужны SEO-friendly URL

    # ===== QUERYSET ОПТИМИЗАЦИЯ =====

    def get_queryset(self):
        """
        Оптимизированный QuerySet с предзагрузкой связанных объектов
        """
        queryset = YourModel.objects.filter(is_active=True)

        # TODO: Добавьте select_related для ForeignKey полей
        # queryset = queryset.select_related("category", "brand")

        # TODO: Добавьте prefetch_related для ManyToMany или обратных ForeignKey
        # queryset = queryset.prefetch_related("tags", "images")

        # TODO: Добавьте аннотации если нужны вычисляемые поля
        # queryset = queryset.annotate(
        #     items_count=Count("items"),
        #     avg_rating=Avg("reviews__rating")
        # )

        return queryset.order_by(*self.ordering)

    def get_serializer_class(self):
        """
        Динамический выбор serializer в зависимости от действия
        """
        if self.action == "list":
            return YourModelListSerializer  # Облегченная версия для списка
        elif self.action == "retrieve":
            return YourModelDetailSerializer  # Полная информация для деталей
        elif self.action == "create":
            return YourModelCreateSerializer  # Поля для создания
        elif self.action in ["update", "partial_update"]:
            return YourModelUpdateSerializer  # Поля для обновления

        return YourModelDetailSerializer  # Fallback

    def get_permissions(self):
        """
        Динамические права доступа в зависимости от действия
        """
        # TODO: Настройте права для разных действий
        if self.action in ["list", "retrieve"]:
            permission_classes = [permissions.AllowAny]
        elif self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = self.permission_classes

        return [permission() for permission in permission_classes]

    # ===== OPENAPI ДОКУМЕНТАЦИЯ =====

    @extend_schema(
        summary="Список объектов YourModel",
        description="Получение списка объектов с фильтрацией, поиском и сортировкой",
        parameters=[
            # TODO: Добавьте параметры фильтрации
            OpenApiParameter(
                "search", OpenApiTypes.STR, description="Поиск по названию и описанию"
            ),
            OpenApiParameter(
                "is_active", OpenApiTypes.BOOL, description="Только активные объекты"
            ),
            OpenApiParameter(
                "ordering",
                OpenApiTypes.STR,
                description="Сортировка: name, -name, created_at, -created_at",
            ),
            # OpenApiParameter("category", OpenApiTypes.INT, description="ID категории"),
            # OpenApiParameter("min_price", OpenApiTypes.NUMBER, description="Минимальная цена"),
            # OpenApiParameter("max_price", OpenApiTypes.NUMBER, description="Максимальная цена"),
        ],
        tags=["YourModel"],  # TODO: Замените на название вашей сущности
    )
    def list(self, request, *args, **kwargs):
        """Получение списка объектов"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Детали объекта YourModel",
        description="Получение детальной информации об объекте",
        tags=["YourModel"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Получение деталей объекта"""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Создание YourModel",
        description="Создание нового объекта",
        tags=["YourModel"],
    )
    def create(self, request, *args, **kwargs):
        """Создание объекта"""
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Обновление YourModel",
        description="Полное обновление объекта",
        tags=["YourModel"],
    )
    def update(self, request, *args, **kwargs):
        """Обновление объекта"""
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Частичное обновление YourModel",
        description="Частичное обновление полей объекта",
        tags=["YourModel"],
    )
    def partial_update(self, request, *args, **kwargs):
        """Частичное обновление объекта"""
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удаление YourModel",
        description="Удаление объекта",
        tags=["YourModel"],
    )
    def destroy(self, request, *args, **kwargs):
        """Удаление объекта"""
        return super().destroy(request, *args, **kwargs)

    # ===== КАСТОМНЫЕ ДЕЙСТВИЯ =====

    @action(detail=False, methods=["get"])
    @extend_schema(
        summary="Популярные объекты",
        description="Получение списка популярных объектов",
        tags=["YourModel"],
    )
    def popular(self, request):
        """
        Получение популярных объектов
        GET /api/your-model/popular/
        """
        # TODO: Реализуйте логику популярности
        queryset = self.get_queryset().order_by("-created_at")[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    @extend_schema(
        summary="Статистика",
        description="Получение статистики по объектам",
        tags=["YourModel"],
    )
    def stats(self, request):
        """
        Статистика по объектам
        GET /api/your-model/stats/
        """
        queryset = self.get_queryset()

        stats = {
            "total_count": queryset.count(),
            "active_count": queryset.filter(is_active=True).count(),
            # TODO: Добавьте нужную статистику
            # 'avg_price': queryset.aggregate(avg_price=Avg('price'))['avg_price'],
            # 'categories_count': queryset.values('category').distinct().count(),
        }

        return Response(stats)

    @action(detail=True, methods=["post"])
    @extend_schema(
        summary="Активировать объект",
        description="Активация деактивированного объекта",
        tags=["YourModel"],
    )
    def activate(self, request, pk=None):
        """
        Активация объекта
        POST /api/your-model/{id}/activate/
        """
        obj = self.get_object()

        if obj.is_active:
            return Response(
                {"message": "Объект уже активен"}, status=status.HTTP_400_BAD_REQUEST
            )

        obj.is_active = True
        obj.save()

        serializer = self.get_serializer(obj)
        return Response(
            {"message": "Объект успешно активирован", "object": serializer.data}
        )

    @action(detail=True, methods=["post"])
    @extend_schema(
        summary="Деактивировать объект",
        description="Деактивация объекта",
        tags=["YourModel"],
    )
    def deactivate(self, request, pk=None):
        """
        Деактивация объекта
        POST /api/your-model/{id}/deactivate/
        """
        obj = self.get_object()

        if not obj.is_active:
            return Response(
                {"message": "Объект уже деактивирован"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj.is_active = False
        obj.save()

        return Response({"message": "Объект успешно деактивирован"})

    # TODO: Добавьте свои кастомные действия
    # Примеры:

    # @action(detail=True, methods=['get'])
    # def related_items(self, request, pk=None):
    #     """Похожие объекты"""
    #     obj = self.get_object()
    #     related = YourModel.objects.filter(category=obj.category).exclude(id=obj.id)[:5]
    #     serializer = YourModelListSerializer(related, many=True, context={'request': request})
    #     return Response(serializer.data)

    # @action(detail=True, methods=['post'])
    # def toggle_favorite(self, request, pk=None):
    #     """Добавить/убрать из избранного"""
    #     obj = self.get_object()
    #     user = request.user
    #
    #     favorite, created = Favorite.objects.get_or_create(user=user, object=obj)
    #     if not created:
    #         favorite.delete()
    #         return Response({'message': 'Удалено из избранного'})
    #
    #     return Response({'message': 'Добавлено в избранное'})

    # ===== ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ =====

    def perform_create(self, serializer):
        """
        Дополнительная логика при создании объекта
        """
        # TODO: Добавьте логику создания
        # Например, привязка к текущему пользователю:
        # serializer.save(created_by=self.request.user)

        serializer.save()

    def perform_update(self, serializer):
        """
        Дополнительная логика при обновлении объекта
        """
        # TODO: Добавьте логику обновления
        # Например, фиксация пользователя который обновил:
        # serializer.save(updated_by=self.request.user)

        serializer.save()

    def perform_destroy(self, instance):
        """
        Дополнительная логика при удалении объекта
        """
        # TODO: Добавьте логику удаления
        # Можете сделать soft delete вместо полного удаления:
        # instance.is_active = False
        # instance.save()

        instance.delete()


# ===== ПРОСТОЙ READONLY VIEWSET =====


class YourModelReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Простой ReadOnly ViewSet для справочников
    Только чтение данных без возможности изменения
    """

    queryset = YourModel.objects.filter(is_active=True)
    serializer_class = YourModelListSerializer
    permission_classes = [permissions.AllowAny]

    # Поиск и фильтрация
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    @extend_schema(tags=["YourModel"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["YourModel"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


# ===== VIEWSET С ИЕРАРХИЕЙ =====


class YourModelCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для категорий с поддержкой иерархии
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = YourModelCategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        """QuerySet с подсчетом объектов в категориях"""
        return (
            YourModelCategory.objects.filter(is_active=True)
            .annotate(items_count=Count("items", filter=Q(items__is_active=True)))
            .prefetch_related(
                Prefetch(
                    "children",
                    queryset=YourModelCategory.objects.filter(is_active=True).annotate(
                        items_count=Count("items", filter=Q(items__is_active=True))
                    ),
                    to_attr="prefetched_children",
                )
            )
            .order_by("sort_order", "name")
        )

    @extend_schema(
        summary="Дерево категорий",
        description="Получение иерархического дерева категорий",
        tags=["Categories"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


# ===== ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ =====


class BulkActionsMixin:
    """
    Миксин для массовых операций
    """

    @action(detail=False, methods=["post"])
    @extend_schema(
        summary="Массовое обновление",
        description="Обновление нескольких объектов одновременно",
    )
    def bulk_update(self, request):
        """
        Массовое обновление объектов
        POST /api/your-model/bulk_update/
        {
            "ids": [1, 2, 3],
            "data": {"is_active": true}
        }
        """
        ids = request.data.get("ids", [])
        update_data = request.data.get("data", {})

        if not ids or not update_data:
            return Response(
                {"error": "Необходимо указать ids и data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_count = self.get_queryset().filter(id__in=ids).update(**update_data)

        return Response(
            {
                "message": f"Обновлено {updated_count} объектов",
                "updated_count": updated_count,
            }
        )

    @action(detail=False, methods=["delete"])
    @extend_schema(
        summary="Массовое удаление",
        description="Удаление нескольких объектов одновременно",
    )
    def bulk_delete(self, request):
        """
        Массовое удаление объектов
        DELETE /api/your-model/bulk_delete/
        {"ids": [1, 2, 3]}
        """
        ids = request.data.get("ids", [])

        if not ids:
            return Response(
                {"error": "Необходимо указать ids"}, status=status.HTTP_400_BAD_REQUEST
            )

        deleted_count, _ = self.get_queryset().filter(id__in=ids).delete()

        return Response(
            {
                "message": f"Удалено {deleted_count} объектов",
                "deleted_count": deleted_count,
            }
        )


# TODO: Используйте миксин если нужны массовые операции
# class YourModelViewSet(BulkActionsMixin, viewsets.ModelViewSet):
