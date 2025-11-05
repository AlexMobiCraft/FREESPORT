from apps.products.models import ImportSession


class IntegrationImportSession(ImportSession):
    class Meta:
        proxy = True
        app_label = "integrations"
        verbose_name = "Сессия импорта"
        verbose_name_plural = "Сессии импорта"
