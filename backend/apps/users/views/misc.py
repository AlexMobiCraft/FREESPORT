"""
Вспомогательные views и утилиты
"""
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from ..models import User


@extend_schema(
    summary="Информация о ролях пользователей",
    description="Получение списка доступных ролей пользователей в системе",
    responses={
        200: OpenApiResponse(
            description="Список ролей пользователей",
            examples={
                "application/json": {
                    "roles": [
                        {"key": "retail", "display": "Розничный покупатель"},
                        {"key": "wholesale_level1", "display": "Оптовик уровень 1"},
                        {"key": "wholesale_level2", "display": "Оптовик уровень 2"},
                        {"key": "wholesale_level3", "display": "Оптовик уровень 3"},
                        {"key": "trainer", "display": "Тренер/Фитнес-клуб"},
                        {"key": "federation_rep", "display": "Представитель федерации"},
                    ]
                }
            },
        )
    },
    tags=["Users"],
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def user_roles_view(request):
    """
    Возвращает список доступных ролей пользователей
    """
    # Исключаем роль admin из публичного API
    public_roles = [choice for choice in User.ROLE_CHOICES if choice[0] != "admin"]

    roles_data = [{"key": role[0], "display": role[1]} for role in public_roles]

    return Response({"roles": roles_data}, status=status.HTTP_200_OK)
