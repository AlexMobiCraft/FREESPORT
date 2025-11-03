from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations"
    verbose_name = "ИНТЕГРАЦИИ"
    
    def ready(self):
        """Импортируем admin при загрузке приложения"""
        import apps.integrations.admin  # noqa: F401