from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django_redis import get_redis_connection

from apps.products.models import Product

from .models import IntegrationImportSession
from .tasks import run_selective_import_task


@admin.register(IntegrationImportSession)
class ImportSessionAdmin(admin.ModelAdmin):
    """Admin для модели ImportSession с мониторингом и запуском импорта"""

    list_display = (
        "id",
        "import_type",
        "colored_status",
        "celery_task_status",
        "started_at",
        "finished_at",
        "duration",
    )
    list_filter = ("status", "import_type", "started_at")
    search_fields = ("id", "error_message")
    readonly_fields = (
        "id",
        "started_at",
        "finished_at",
        "report_details",
        "celery_task_id",
    )
    actions = ["trigger_selective_import"]

    class Media:
        """Добавляем JavaScript для автообновления страницы"""

        js = ("admin/js/import_session_auto_refresh.js",)

    fieldsets = (
        (
            "Основная информация",
            {
                "fields": ("id", "import_type", "status", "celery_task_id"),
            },
        ),
        (
            "Детали",
            {
                "fields": (
                    "report_details",
                    "error_message",
                ),
            },
        ),
        (
            "Временные метки",
            {
                "fields": ("started_at", "finished_at"),
            },
        ),
    )

    @admin.action(description="🚀 Запустить импорт из 1С")
    def trigger_selective_import(
        self, request: HttpRequest, queryset: QuerySet
    ) -> TemplateResponse | None:
        """
        Запуск выборочного импорта данных из 1С с intermediate page.

        Показывает форму выбора типов данных для импорта:
        - Каталог товаров
        - Остатки товаров
        - Цены товаров
        - Клиенты

        Использует distributed lock через Redis для предотвращения
        одновременного запуска нескольких импортов.
        """
        # Если форма отправлена - обрабатываем импорт
        if "apply" in request.POST:
            selected_types = request.POST.getlist("import_types")

            if not selected_types:
                self.message_user(
                    request,
                    "⚠️ Не выбрано ни одного типа данных для импорта.",
                    level="WARNING",
                )
                return None

            # Валидация зависимостей
            is_valid, error_message = self._validate_dependencies(selected_types)
            if not is_valid:
                self.message_user(request, error_message, level="ERROR")
                return None

            # Запуск последовательного импорта
            self._run_sequential_import(request, selected_types)
            return None

        # Показываем intermediate page с формой выбора
        context = {
            **self.admin_site.each_context(request),
            "title": "Выбор типов данных для импорта",
            "queryset": queryset,
            "opts": self.model._meta,
            "action": "trigger_selective_import",
        }
        return TemplateResponse(
            request, "admin/integrations/import_selection.html", context
        )

    def _validate_dependencies(self, selected_types: list[str]) -> tuple[bool, str]:
        """
        Проверка зависимостей между типами импорта.

        Args:
            selected_types: Список выбранных типов импорта

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        # Проверяем зависимости остатков и цен от каталога
        if "stocks" in selected_types or "prices" in selected_types:
            if "catalog" not in selected_types:
                # Проверяем наличие товаров в БД
                if not Product.objects.exists():
                    return (
                        False,
                        "⚠️ Невозможно загрузить остатки/цены: "
                        "каталог товаров пуст. Сначала импортируйте каталог "
                        "или выберите 'Каталог товаров' для импорта.",
                    )
        return True, ""

    def _run_sequential_import(
        self, request: HttpRequest, selected_types: list[str]
    ) -> None:
        """
        Запуск асинхронного импорта через Celery с Redis lock.

        Args:
            request: HTTP запрос
            selected_types: Список выбранных типов импорта
        """
        import logging

        logger = logging.getLogger(__name__)

        # Генерируем уникальный ID запроса для отслеживания
        import uuid

        request_id = str(uuid.uuid4())[:8]
        logger.info(f"[Request {request_id}] Попытка запуска импорта: {selected_types}")

        redis_conn = get_redis_connection("default")
        lock_key = "import_catalog_lock"
        lock = redis_conn.lock(lock_key, timeout=3600)  # 1 час TTL

        # Пытаемся захватить блокировку (non-blocking)
        if not lock.acquire(blocking=False):
            logger.warning(
                f"[Request {request_id}] Импорт уже запущен, блокировка активна"
            )
            self.message_user(
                request,
                "⚠️ Импорт уже запущен! Дождитесь завершения текущего импорта.",
                level="WARNING",
            )
            return

        try:
            # Проверяем наличие настройки ONEC_DATA_DIR
            data_dir = getattr(settings, "ONEC_DATA_DIR", None)
            if not data_dir:
                raise ValueError(
                    "Настройка ONEC_DATA_DIR не найдена в settings. "
                    "Убедитесь, что путь к данным 1С настроен."
                )

            # Создаем новую сессию импорта для отслеживания
            from apps.products.models import ImportSession

            # Определяем тип сессии на основе выбранных типов
            # Если выбрано несколько типов, используем первый
            session_type_map = {
                "catalog": ImportSession.ImportType.CATALOG,
                "stocks": ImportSession.ImportType.STOCKS,
                "prices": ImportSession.ImportType.PRICES,
                "customers": ImportSession.ImportType.CUSTOMERS,
            }

            primary_type = selected_types[0] if selected_types else "catalog"
            session_import_type = session_type_map.get(
                primary_type, ImportSession.ImportType.CATALOG
            )

            session = ImportSession.objects.create(
                import_type=session_import_type,
                status=ImportSession.ImportStatus.STARTED,
            )

            # Запускаем асинхронную задачу Celery
            task = run_selective_import_task.delay(selected_types, str(data_dir))

            # Сохраняем task_id в сессию
            session.celery_task_id = task.id
            session.save(update_fields=["celery_task_id"])

            logger.info(
                f"[Request {request_id}] Импорт запущен успешно. "
                f"Session ID: {session.pk}, Task ID: {task.id}, Types: {selected_types}"
            )

            self.message_user(
                request,
                f"✅ Импорт запущен в фоновом режиме (Task ID: {task.id}). "
                f"Отслеживайте прогресс в разделе 'Сессии импорта' (ID: {session.pk}).",
                level="SUCCESS",
            )

        except Exception as e:
            self.message_user(
                request,
                f"❌ Ошибка запуска импорта: {e}",
                level="ERROR",
            )
        finally:
            # Освобождаем lock сразу после запуска задачи
            # Задача сама будет управлять процессом импорта
            lock.release()

    @admin.display(description="Статус")
    def colored_status(self, obj: IntegrationImportSession) -> str:
        """
        Отображение статуса с цветовой индикацией и иконками.

        - 🟢 Зеленый: completed
        - 🟡 Желтый: in_progress
        - 🔴 Красный: failed
        - ⚪ Серый: started
        """
        colors = {
            "completed": "green",
            "in_progress": "orange",
            "failed": "red",
            "started": "gray",
        }
        icons = {
            "completed": "✅",
            "in_progress": "⏳",
            "failed": "❌",
            "started": "⏸️",
        }
        color = colors.get(obj.status, "black")
        icon = icons.get(obj.status, "❓")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_status_display(),
        )

    @admin.display(description="Celery Task")
    def celery_task_status(self, obj: IntegrationImportSession) -> str:
        """
        Отображение статуса Celery задачи в реальном времени.

        Проверяет статус задачи через Celery API и показывает:
        - PENDING: задача в очереди
        - STARTED: задача выполняется
        - SUCCESS: задача завершена успешно
        - FAILURE: задача завершена с ошибкой
        - RETRY: задача ожидает повторной попытки
        """
        if not obj.celery_task_id:
            return format_html('<span style="color: gray;">-</span>')

        try:
            from celery.result import AsyncResult

            task_result = AsyncResult(obj.celery_task_id)
            state = task_result.state

            # Маппинг статусов на иконки и цвета
            status_map = {
                "PENDING": ("⏳", "gray", "В очереди"),
                "STARTED": ("▶️", "blue", "Выполняется"),
                "SUCCESS": ("✅", "green", "Завершено"),
                "FAILURE": ("❌", "red", "Ошибка"),
                "RETRY": ("🔄", "orange", "Повтор"),
            }

            icon, color, label = status_map.get(state, ("❓", "black", state))

            return format_html(
                '<span style="color: {}; font-weight: bold;" title="Task ID: {}">{} {}</span>',
                color,
                obj.celery_task_id,
                icon,
                label,
            )
        except Exception:
            return format_html(
                '<span style="color: gray;" title="{}">⚠️ Недоступно</span>',
                obj.celery_task_id,
            )

    @admin.display(description="Длительность")
    def duration(self, obj: IntegrationImportSession) -> str:
        """
        Расчет длительности импорта.

        Показывает время в минутах если импорт завершен,
        или "В процессе..." если еще выполняется.
        """
        if obj.finished_at and obj.started_at:
            delta = obj.finished_at - obj.started_at
            minutes = delta.total_seconds() / 60
            if minutes < 1:
                seconds = delta.total_seconds()
                return f"{seconds:.0f} сек"
            return f"{minutes:.1f} мин"
        elif obj.started_at:
            return "В процессе..."
        return "-"

    @admin.display(description="Прогресс")
    def progress_display(self, obj: IntegrationImportSession) -> str:
        """
        Отображение прогресс-бара для импортов в процессе выполнения.

        Показывает HTML5 progress bar с процентами, если:
        - Статус: in_progress
        - Есть данные о total_items в report_details
        """
        if obj.status == "in_progress" and obj.report_details:
            total = obj.report_details.get("total_items", 0)
            processed = obj.report_details.get("processed_items", 0)

            if total > 0:
                progress = (processed / total) * 100
                progress_percent = f"{progress:.0f}"
                progress_bar = (
                    '<progress value="{}" max="100" '
                    'style="width: 150px; height: 20px;"></progress> '
                    '<span style="font-weight: bold;">{}%</span> ({}/{})'
                )
                return format_html(
                    progress_bar,
                    progress,
                    progress_percent,
                    processed,
                    total,
                )
        return "-"
