from apps.products.models import ImportSession


class IntegrationImportSession(ImportSession):
    """
    Proxy модель для отображения сессий импорта в Django Admin.

    URL страницы в admin: /admin/integrations/session/
    (Django генерирует URL на основе app_label + model_name в lowercase)
    """

    class Meta:
        proxy = True
        app_label = "integrations"
        verbose_name = "Сессия"
        verbose_name_plural = "Сессии"
        # Изменили verbose_name_plural с "Сессии импорта" на "Сессии"
        # для получения короткого URL: /admin/integrations/session/
        # вместо /admin/integrations/integrationimportsession/
