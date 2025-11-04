"""
Интеграционные тесты для выборочного импорта данных из 1С через админ-панель.
Story 9.5: Selective Import UI
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.http import HttpRequest
from django.test import RequestFactory
from django_redis import get_redis_connection

from apps.integrations.admin import ImportSessionAdmin
from apps.products.models import ImportSession, Product

if TYPE_CHECKING:
    from django.contrib.auth.models import User as UserType

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user() -> UserType:
    """Создает пользователя-администратора"""
    return User.objects.create_superuser(
        email="admin@test.com",
        password="testpass123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def import_session() -> ImportSession:
    """Создает тестовую сессию импорта"""
    return ImportSession.objects.create(
        import_type=ImportSession.ImportType.CATALOG,
        status=ImportSession.ImportStatus.COMPLETED,
    )


@pytest.fixture
def admin_site() -> AdminSite:
    """Создает инстанс AdminSite"""
    return AdminSite()


@pytest.fixture
def import_session_admin(admin_site: AdminSite) -> ImportSessionAdmin:
    """Создает инстанс ImportSessionAdmin"""
    return ImportSessionAdmin(ImportSession, admin_site)


@pytest.fixture
def mock_request(admin_user: UserType) -> HttpRequest:
    """Создает мок HTTP запроса с авторизованным пользователем"""
    factory = RequestFactory()
    request = factory.post("/admin/integrations/importsession/")
    request.user = admin_user
    # Добавляем session для messages framework
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.contrib.messages.middleware import MessageMiddleware

    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()

    messages_middleware = MessageMiddleware(lambda req: None)
    messages_middleware.process_request(request)

    return request


@pytest.fixture(autouse=True)
def clear_redis():
    """Очищает Redis перед каждым тестом"""
    redis_conn = get_redis_connection("default")
    redis_conn.delete("import_catalog_lock")
    yield
    redis_conn.delete("import_catalog_lock")


class TestValidateDependencies:
    """Тесты валидации зависимостей между типами импорта"""

    def test_validate_stocks_without_catalog_empty_db(
        self, import_session_admin: ImportSessionAdmin
    ):
        """Тест: остатки без каталога + пустая БД → ошибка"""
        # Убедимся что БД пуста
        Product.objects.all().delete()

        selected_types = ["stocks"]
        is_valid, error_message = import_session_admin._validate_dependencies(
            selected_types
        )

        assert is_valid is False
        assert "каталог товаров пуст" in error_message
        assert "Сначала импортируйте каталог" in error_message

    def test_validate_prices_without_catalog_empty_db(
        self, import_session_admin: ImportSessionAdmin
    ):
        """Тест: цены без каталога + пустая БД → ошибка"""
        Product.objects.all().delete()

        selected_types = ["prices"]
        is_valid, error_message = import_session_admin._validate_dependencies(
            selected_types
        )

        assert is_valid is False
        assert "каталог товаров пуст" in error_message

    def test_validate_stocks_without_catalog_with_products(
        self, import_session_admin: ImportSessionAdmin
    ):
        """Тест: остатки без каталога + есть товары в БД → OK"""
        # Создаем необходимые зависимости
        from apps.products.models import Brand, Category

        brand = Brand.objects.create(
            name="Test Brand", slug="test-brand", onec_id="test-brand-uuid"
        )
        category = Category.objects.create(
            name="Test Category", slug="test-category", onec_id="test-category-uuid"
        )

        # Создаем тестовый товар
        Product.objects.create(
            name="Test Product",
            slug="test-product",
            onec_id="test-uuid",
            retail_price=100.00,
            brand=brand,
            category=category,
        )

        selected_types = ["stocks"]
        is_valid, error_message = import_session_admin._validate_dependencies(
            selected_types
        )

        assert is_valid is True
        assert error_message == ""

    def test_validate_stocks_with_catalog(
        self, import_session_admin: ImportSessionAdmin
    ):
        """Тест: остатки + каталог → OK (независимо от БД)"""
        Product.objects.all().delete()

        selected_types = ["catalog", "stocks"]
        is_valid, error_message = import_session_admin._validate_dependencies(
            selected_types
        )

        assert is_valid is True
        assert error_message == ""

    def test_validate_customers_only(self, import_session_admin: ImportSessionAdmin):
        """Тест: только клиенты → OK (не зависят от каталога)"""
        Product.objects.all().delete()

        selected_types = ["customers"]
        is_valid, error_message = import_session_admin._validate_dependencies(
            selected_types
        )

        assert is_valid is True
        assert error_message == ""


class TestExecuteImport:
    """Тесты выполнения импорта конкретного типа"""

    @patch("apps.integrations.admin.call_command")
    def test_execute_catalog_import(
        self, mock_call_command: Mock, import_session_admin: ImportSessionAdmin, tmp_path: Path
    ):
        """Тест: импорт каталога вызывает правильную команду"""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        result = import_session_admin._execute_import("catalog", str(data_dir))

        assert result == {"type": "catalog", "message": "Каталог импортирован"}
        mock_call_command.assert_called_once_with(
            "import_catalog_from_1c",
            "--data-dir",
            str(data_dir),
            "--file-type",
            "all",
        )

    @patch("apps.integrations.admin.call_command")
    def test_execute_stocks_import(
        self, mock_call_command: Mock, import_session_admin: ImportSessionAdmin, tmp_path: Path
    ):
        """Тест: импорт остатков вызывает правильную команду"""
        data_dir = tmp_path / "data"
        rests_dir = data_dir / "rests"
        rests_dir.mkdir(parents=True)
        rests_file = rests_dir / "rests.xml"
        rests_file.write_text("<root></root>")

        result = import_session_admin._execute_import("stocks", str(data_dir))

        assert result == {"type": "stocks", "message": "Остатки обновлены"}
        mock_call_command.assert_called_once_with(
            "load_product_stocks", "--file", str(rests_file)
        )

    @patch("apps.integrations.admin.call_command")
    def test_execute_prices_import(
        self, mock_call_command: Mock, import_session_admin: ImportSessionAdmin, tmp_path: Path
    ):
        """Тест: импорт цен вызывает правильную команду"""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        result = import_session_admin._execute_import("prices", str(data_dir))

        assert result == {"type": "prices", "message": "Цены обновлены"}
        mock_call_command.assert_called_once_with(
            "import_catalog_from_1c",
            "--data-dir",
            str(data_dir),
            "--file-type",
            "prices",
        )

    @patch("apps.integrations.admin.call_command")
    def test_execute_customers_import(
        self, mock_call_command: Mock, import_session_admin: ImportSessionAdmin, tmp_path: Path
    ):
        """Тест: импорт клиентов вызывает правильную команду"""
        data_dir = tmp_path / "data"
        contragents_dir = data_dir / "contragents"
        contragents_dir.mkdir(parents=True)
        contragents_file = contragents_dir / "contragents_1_test.xml"
        contragents_file.write_text("<root></root>")

        result = import_session_admin._execute_import("customers", str(data_dir))

        assert result == {"type": "customers", "message": "Клиенты импортированы"}
        mock_call_command.assert_called_once_with(
            "import_customers_from_1c", "--file", str(contragents_file)
        )

    def test_execute_import_missing_directory(
        self, import_session_admin: ImportSessionAdmin
    ):
        """Тест: отсутствующая директория → FileNotFoundError"""
        with pytest.raises(FileNotFoundError) as exc_info:
            import_session_admin._execute_import("catalog", "/nonexistent/path")

        assert "Директория данных не найдена" in str(exc_info.value)

    def test_execute_import_missing_stocks_file(
        self, import_session_admin: ImportSessionAdmin, tmp_path: Path
    ):
        """Тест: отсутствующий файл остатков → FileNotFoundError"""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        with pytest.raises(FileNotFoundError) as exc_info:
            import_session_admin._execute_import("stocks", str(data_dir))

        assert "Файл остатков не найден" in str(exc_info.value)
        assert "rests.xml" in str(exc_info.value)

    def test_execute_import_missing_customers_directory(
        self, import_session_admin: ImportSessionAdmin, tmp_path: Path
    ):
        """Тест: отсутствующая директория контрагентов → FileNotFoundError"""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        with pytest.raises(FileNotFoundError) as exc_info:
            import_session_admin._execute_import("customers", str(data_dir))

        assert "Директория контрагентов не найдена" in str(exc_info.value)

    def test_execute_import_unknown_type(
        self, import_session_admin: ImportSessionAdmin, tmp_path: Path
    ):
        """Тест: неизвестный тип импорта → ValueError"""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        with pytest.raises(ValueError) as exc_info:
            import_session_admin._execute_import("unknown", str(data_dir))

        assert "Неизвестный тип импорта" in str(exc_info.value)


class TestSequentialImport:
    """Тесты последовательного запуска импортов"""

    @patch("apps.integrations.admin.ImportSessionAdmin._execute_import")
    @patch("apps.integrations.admin.settings")
    def test_sequential_import_catalog_and_stocks(
        self,
        mock_settings: Mock,
        mock_execute: Mock,
        import_session_admin: ImportSessionAdmin,
        mock_request: HttpRequest,
        import_session: ImportSession,
    ):
        """Тест: последовательный импорт каталога и остатков"""
        mock_settings.ONEC_DATA_DIR = "/test/data"
        mock_execute.side_effect = [
            {"type": "catalog", "message": "Каталог импортирован"},
            {"type": "stocks", "message": "Остатки обновлены"},
        ]

        queryset = ImportSession.objects.filter(pk=import_session.pk)
        mock_request.POST = {"apply": "true", "import_types": ["catalog", "stocks"]}

        import_session_admin._run_sequential_import(
            mock_request, ["catalog", "stocks"]
        )

        # Проверяем что оба импорта выполнены
        assert mock_execute.call_count == 2
        mock_execute.assert_any_call("catalog", "/test/data")
        mock_execute.assert_any_call("stocks", "/test/data")

        # Проверяем success сообщение
        messages = list(get_messages(mock_request))
        assert len(messages) == 1
        assert "Импорт завершен" in str(messages[0])
        assert "Каталог импортирован" in str(messages[0])
        assert "Остатки обновлены" in str(messages[0])

    @patch("apps.integrations.admin.ImportSessionAdmin._execute_import")
    @patch("apps.integrations.admin.settings")
    def test_sequential_import_catalog_failed_stocks_not_started(
        self,
        mock_settings: Mock,
        mock_execute: Mock,
        import_session_admin: ImportSessionAdmin,
        mock_request: HttpRequest,
        import_session: ImportSession,
    ):
        """Тест: ошибка при импорте каталога → остатки не импортируются"""
        mock_settings.ONEC_DATA_DIR = "/test/data"
        mock_execute.side_effect = FileNotFoundError("Test error")

        import_session_admin._run_sequential_import(
            mock_request, ["catalog", "stocks"]
        )

        # Проверяем что вызван только один импорт (каталог)
        assert mock_execute.call_count == 1
        mock_execute.assert_called_once_with("catalog", "/test/data")

        # Проверяем error сообщение
        messages = list(get_messages(mock_request))
        assert len(messages) == 1
        assert "Ошибка импорта каталога" in str(messages[0])
        assert "Последующие импорты отменены" in str(messages[0])

    @patch("apps.integrations.admin.settings")
    def test_sequential_import_missing_onec_data_dir(
        self,
        mock_settings: Mock,
        import_session_admin: ImportSessionAdmin,
        mock_request: HttpRequest,
    ):
        """Тест: отсутствие ONEC_DATA_DIR → критическая ошибка"""
        mock_settings.ONEC_DATA_DIR = None

        import_session_admin._run_sequential_import(mock_request, ["catalog"])

        # Проверяем critical error сообщение
        messages = list(get_messages(mock_request))
        assert len(messages) == 1
        assert "Критическая ошибка" in str(messages[0])
        assert "ONEC_DATA_DIR" in str(messages[0])


class TestConcurrentImportPrevention:
    """Тесты предотвращения concurrent запусков"""

    @patch("apps.integrations.admin.ImportSessionAdmin._execute_import")
    @patch("apps.integrations.admin.settings")
    def test_concurrent_import_prevention(
        self,
        mock_settings: Mock,
        mock_execute: Mock,
        import_session_admin: ImportSessionAdmin,
        mock_request: HttpRequest,
    ):
        """Тест: второй импорт блокируется пока первый выполняется"""
        mock_settings.ONEC_DATA_DIR = "/test/data"

        redis_conn = get_redis_connection("default")
        lock = redis_conn.lock("import_catalog_lock", timeout=10)
        lock.acquire(blocking=False)

        try:
            import_session_admin._run_sequential_import(mock_request, ["catalog"])

            # Проверяем что импорт НЕ выполнен
            mock_execute.assert_not_called()

            # Проверяем warning сообщение
            messages = list(get_messages(mock_request))
            assert len(messages) == 1
            assert "Импорт уже запущен" in str(messages[0])
        finally:
            lock.release()


class TestFormatImportSummary:
    """Тесты форматирования сводки результатов"""

    def test_format_summary_single_import(
        self, import_session_admin: ImportSessionAdmin
    ):
        """Тест: форматирование сводки для одного импорта"""
        results = [{"type": "catalog", "message": "Каталог импортирован"}]
        summary = import_session_admin._format_import_summary(results)

        assert summary == "Импорт завершен: Каталог импортирован"

    def test_format_summary_multiple_imports(
        self, import_session_admin: ImportSessionAdmin
    ):
        """Тест: форматирование сводки для нескольких импортов"""
        results = [
            {"type": "catalog", "message": "Каталог импортирован"},
            {"type": "stocks", "message": "Остатки обновлены"},
            {"type": "customers", "message": "Клиенты импортированы"},
        ]
        summary = import_session_admin._format_import_summary(results)

        assert summary == "Импорт завершен: Каталог импортирован, Остатки обновлены, Клиенты импортированы"

    def test_format_summary_empty_results(
        self, import_session_admin: ImportSessionAdmin
    ):
        """Тест: форматирование сводки для пустого списка"""
        results = []
        summary = import_session_admin._format_import_summary(results)

        assert summary == "Импорт завершен (0 операций)"


class TestIntermediatePageRendering:
    """Тесты отображения intermediate page"""

    def test_intermediate_page_renders_without_apply(
        self,
        import_session_admin: ImportSessionAdmin,
        mock_request: HttpRequest,
        import_session: ImportSession,
    ):
        """Тест: без 'apply' в POST → показывается форма выбора"""
        queryset = ImportSession.objects.filter(pk=import_session.pk)
        mock_request.POST = {}

        response = import_session_admin.trigger_selective_import(
            mock_request, queryset
        )

        assert response is not None
        assert response.template_name == "admin/integrations/import_selection.html"
        assert "queryset" in response.context_data

    @patch("apps.integrations.admin.ImportSessionAdmin._run_sequential_import")
    @patch("apps.integrations.admin.ImportSessionAdmin._validate_dependencies")
    def test_intermediate_page_with_apply(
        self,
        mock_validate: Mock,
        mock_run_import: Mock,
        import_session_admin: ImportSessionAdmin,
        admin_user: UserType,
        import_session: ImportSession,
    ):
        """Тест: с 'apply' в POST → запускается импорт"""
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        from django.test import RequestFactory

        mock_validate.return_value = (True, "")
        queryset = ImportSession.objects.filter(pk=import_session.pk)

        # Создаем правильный request с QueryDict
        factory = RequestFactory()
        request = factory.post(
            "/admin/integrations/importsession/",
            data={"apply": "true", "import_types": ["catalog"]},
        )
        request.user = admin_user

        # Добавляем middleware
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()

        messages_middleware = MessageMiddleware(lambda req: None)
        messages_middleware.process_request(request)

        response = import_session_admin.trigger_selective_import(request, queryset)

        assert response is None  # Редирект после обработки
        mock_validate.assert_called_once_with(["catalog"])
        mock_run_import.assert_called_once()

    def test_intermediate_page_no_types_selected(
        self,
        import_session_admin: ImportSessionAdmin,
        admin_user: UserType,
        import_session: ImportSession,
    ):
        """Тест: не выбрано ни одного типа → warning сообщение"""
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        from django.test import RequestFactory

        queryset = ImportSession.objects.filter(pk=import_session.pk)

        # Создаем правильный request с QueryDict (пустой список)
        factory = RequestFactory()
        request = factory.post(
            "/admin/integrations/importsession/", data={"apply": "true"}
        )
        request.user = admin_user

        # Добавляем middleware
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()

        messages_middleware = MessageMiddleware(lambda req: None)
        messages_middleware.process_request(request)

        response = import_session_admin.trigger_selective_import(request, queryset)

        assert response is None
        messages = list(get_messages(request))
        assert len(messages) == 1
        assert "Не выбрано ни одного типа" in str(messages[0])

    def test_intermediate_page_empty_queryset(
        self,
        import_session_admin: ImportSessionAdmin,
        mock_request: HttpRequest,
    ):
        """Тест: пустой queryset → info сообщение"""
        queryset = ImportSession.objects.none()
        mock_request.POST = {}

        response = import_session_admin.trigger_selective_import(
            mock_request, queryset
        )

        assert response is None
        messages = list(get_messages(mock_request))
        assert len(messages) == 1
        assert "выберите хотя бы одну сессию" in str(messages[0])
