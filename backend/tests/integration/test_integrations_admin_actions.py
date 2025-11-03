"""
Интеграционные тесты для admin actions приложения integrations
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.integrations.models import IntegrationImportSession

User = get_user_model()


@pytest.mark.django_db
class TestImportSessionAdminActions:
    """Интеграционные тесты для действий в Django Admin"""

    @pytest.fixture
    def admin_user(self):
        """Создание администратора для доступа к admin панели"""
        return User.objects.create_superuser(
            email="admin@test.com",
            password="testpass123"
        )

    @pytest.fixture
    def client(self, admin_user):
        """Создание аутентифицированного клиента"""
        client = Client()
        client.force_login(admin_user)
        return client

    @pytest.fixture
    def import_sessions(self):
        """Создание тестовых сессий импорта"""
        sessions = []
        for i in range(3):
            session = IntegrationImportSession.objects.create(
                import_type="catalog",
                status="completed"
            )
            sessions.append(session)
        return sessions

    def test_admin_changelist_page_loads(self, client):
        """
        Тест: страница списка сессий импорта загружается
        """
        # Arrange
        url = reverse("admin:integrations_integrationimportsession_changelist")
        
        # Act
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert "Сессии импорта" in str(response.content)

    def test_admin_filter_by_import_type(self, client, import_sessions):
        """
        Тест: фильтрация по типу импорта работает корректно
        """
        # Arrange
        url = reverse("admin:integrations_integrationimportsession_changelist")
        
        # Act
        response = client.get(url, {"import_type": "catalog"})
        
        # Assert
        assert response.status_code == 200
        # Проверяем, что все 3 сессии отображаются
        content = str(response.content)
        for session in import_sessions:
            assert str(session.id) in content

    def test_admin_action_without_selection(self, client, import_sessions):
        """
        Тест: попытка выполнить действие без выбора объектов
        
        Проверяет, что при отсутствии выбранных объектов
        пользователь получает информационное сообщение.
        """
        # Arrange
        url = reverse("admin:integrations_integrationimportsession_changelist")
        
        # Act - отправляем POST без выбранных объектов
        response = client.post(
            url,
            {
                "action": "trigger_catalog_import",
                "_selected_action": [],  # Пустой список выбранных объектов
            },
            follow=True
        )
        
        # Assert
        assert response.status_code == 200
        # Проверяем наличие информационного сообщения
        messages = list(response.context["messages"])
        assert len(messages) > 0
        # Сообщение должно содержать текст о необходимости выбора
        message_text = str(messages[0])
        assert "выберите" in message_text.lower() or "необходимо" in message_text.lower()

    def test_admin_action_with_selection_and_filter(self, client, import_sessions):
        """
        Тест: выполнение действия с выбранными объектами при активном фильтре
        
        Это основной тест для проверки исправления бага:
        - Применяем фильтр по типу импорта
        - Выбираем объекты
        - Выполняем действие
        - Проверяем, что действие получает выбранные объекты
        """
        # Arrange
        url = reverse("admin:integrations_integrationimportsession_changelist")
        selected_session = import_sessions[0]
        
        # Act - отправляем POST с выбранным объектом и активным фильтром
        response = client.post(
            url,
            {
                "action": "trigger_catalog_import",
                "_selected_action": [str(selected_session.id)],
                "import_type": "catalog",  # Активный фильтр
            },
            follow=True
        )
        
        # Assert
        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert len(messages) > 0
        
        # Проверяем, что действие было выполнено
        # (либо успешно, либо с ошибкой о блокировке/настройках,
        # но НЕ с ошибкой о том, что объекты не выбраны)
        message_text = str(messages[0]).lower()
        assert "объекты не были изменены" not in message_text
        assert "необходимо их выбрать" not in message_text

    def test_admin_list_display_fields(self, client, import_sessions):
        """
        Тест: проверка отображения полей в списке
        """
        # Arrange
        url = reverse("admin:integrations_integrationimportsession_changelist")
        
        # Act
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        content = str(response.content)
        
        # Проверяем наличие заголовков колонок
        assert "Тип импорта" in content or "import_type" in content
        assert "Статус" in content or "status" in content
        assert "Длительность" in content or "duration" in content

    def test_admin_search_functionality(self, client):
        """
        Тест: функциональность поиска в admin панели
        """
        # Arrange
        session_with_error = IntegrationImportSession.objects.create(
            import_type="catalog",
            status="failed",
            error_message="Test error message for search"
        )
        url = reverse("admin:integrations_integrationimportsession_changelist")
        
        # Act
        response = client.get(url, {"q": "Test error message"})
        
        # Assert
        assert response.status_code == 200
        content = str(response.content)
        assert str(session_with_error.id) in content

    def test_admin_detail_page_readonly_fields(self, client, import_sessions):
        """
        Тест: проверка readonly полей на странице детального просмотра
        """
        # Arrange
        session = import_sessions[0]
        url = reverse(
            "admin:integrations_integrationimportsession_change",
            args=[session.id]
        )
        
        # Act
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        content = str(response.content)
        
        # Проверяем наличие readonly полей
        assert "started_at" in content.lower()
        assert "finished_at" in content.lower()
