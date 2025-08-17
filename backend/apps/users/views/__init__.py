"""
Views для API управления пользователями
Разделенные по модулям для лучшей организации кода
"""

# Импорты для совместимости с существующими URL patterns
from .authentication import UserRegistrationView, UserLoginView
from .profile import UserProfileView
from .misc import user_roles_view
from .personal_cabinet import (
    UserDashboardView,
    AddressViewSet,
    FavoriteViewSet,
    OrderHistoryView,
)

__all__ = [
    "UserRegistrationView",
    "UserLoginView",
    "UserProfileView",
    "user_roles_view",
    "UserDashboardView",
    "AddressViewSet",
    "FavoriteViewSet",
    "OrderHistoryView",
]
