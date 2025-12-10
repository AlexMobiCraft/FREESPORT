"""
Views для API управления пользователями
Разделенные по модулям для лучшей организации кода
"""

# Импорты для совместимости с существующими URL patterns
from .authentication import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    UserLoginView,
    UserRegistrationView,
    ValidateTokenView,
)
from .misc import user_roles_view
from .personal_cabinet import (
    AddressViewSet,
    FavoriteViewSet,
    OrderHistoryView,
    UserDashboardView,
)
from .profile import UserProfileView

__all__ = [
    "UserRegistrationView",
    "UserLoginView",
    "UserProfileView",
    "user_roles_view",
    "UserDashboardView",
    "AddressViewSet",
    "FavoriteViewSet",
    "OrderHistoryView",
    "PasswordResetRequestView",
    "PasswordResetConfirmView",
    "ValidateTokenView",
]
