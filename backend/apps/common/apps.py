from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Error, Tags, register

SIGNED_COOKIE_SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"


@register(Tags.compatibility)
def check_session_engine_for_subscribe_consent(app_configs, **kwargs):
    """Проверить, что anonymous subscribe consent может получить session_key."""
    if settings.SESSION_ENGINE != SIGNED_COOKIE_SESSION_ENGINE:
        return []

    return [
        Error(
            "Подписка на рассылку требует server-side session_key для anonymous UserConsent.",
            hint=(
                "Используйте django.contrib.sessions.backends.db или другой server-side "
                "SESSION_ENGINE; signed_cookies не создаёт request.session.session_key."
            ),
            id="common.E001",
        )
    ]


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    verbose_name = "Общие утилиты"
