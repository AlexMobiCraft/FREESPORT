from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib import admin
from django.core.management import call_command
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django_redis import get_redis_connection

from apps.products.models import Product

from .models import IntegrationImportSession


@admin.register(IntegrationImportSession)
class ImportSessionAdmin(admin.ModelAdmin):
    """Admin для модели ImportSession с мониторингом и запуском импорта"""

    list_display = (
        "id",
        "import_type",
        "colored_status",
        "started_at",
        "duration",
        "progress_display",
    )
    list_filter = ("status", "import_type", "started_at")
    search_fields = ("id", "error_message")
    readonly_fields = (
        "id",
        "started_at",
        "finished_at",
        "report_details",
    )
    actions = ["trigger_selective_import"]
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": ("id", "import_type", "status"),
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
        # Проверка: действие не зависит от выбранных объектов
        if not queryset.exists():
            self.message_user(
                request,
                "ℹ️ Для запуска действия выберите хотя бы одну сессию импорта. "
                "Действие создаст новую сессию импорта независимо от выбора.",
                level="INFO",
            )
            return None

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
        Последовательный запуск импортов с Redis lock.

        Args:
            request: HTTP запрос
            selected_types: Список выбранных типов импорта
        """
        redis_conn = get_redis_connection("default")
        lock_key = "import_catalog_lock"
        lock = redis_conn.lock(lock_key, timeout=3600)  # 1 час TTL

        # Пытаемся захватить блокировку (non-blocking)
        if not lock.acquire(blocking=False):
            self.message_user(
                request,
                "⚠️ Импорт уже запущен! Дождитесь завершения текущего импорта.",
                level="WARNING",
            )
            return

        results: list[dict[str, str]] = []
        try:
            # Проверяем наличие настройки ONEC_DATA_DIR
            data_dir = getattr(settings, "ONEC_DATA_DIR", None)
            if not data_dir:
                raise ValueError(
                    "Настройка ONEC_DATA_DIR не найдена в settings. "
                    "Убедитесь, что путь к данным 1С настроен."
                )

            # Порядок импорта: catalog → stocks → prices → customers
            import_order = ["catalog", "stocks", "prices", "customers"]

            for import_type in import_order:
                if import_type not in selected_types:
                    continue

                try:
                    result = self._execute_import(import_type, data_dir)
                    results.append(result)
                except Exception as e:
                    # При ошибке прерываем цепочку
                    import_type_names = {
                        "catalog": "каталога",
                        "stocks": "остатков",
                        "prices": "цен",
                        "customers": "клиентов",
                    }
                    type_name = import_type_names.get(import_type, import_type)
                    self.message_user(
                        request,
                        f"❌ Ошибка импорта {type_name}: {e}. "
                        f"Последующие импорты отменены.",
                        level="ERROR",
                    )
                    return

            # Формируем сводное сообщение
            summary = self._format_import_summary(results)
            self.message_user(request, f"✅ {summary}", level="SUCCESS")

        except Exception as e:
            self.message_user(request, f"❌ Критическая ошибка: {e}", level="ERROR")
        finally:
            # Всегда освобождаем lock
            lock.release()

    def _execute_import(self, import_type: str, data_dir: Any) -> dict[str, str]:
        """
        Выполнение импорта конкретного типа с валидацией файлов.

        Args:
            import_type: Тип импорта (catalog, stocks, prices, customers)
            data_dir: Директория с данными 1С

        Returns:
            Dict с результатом импорта

        Raises:
            FileNotFoundError: Если файл не найден
            Exception: При ошибках выполнения команды
        """
        data_path = Path(data_dir)

        if import_type == "catalog":
            # Для каталога проверяем директорию
            if not data_path.exists():
                raise FileNotFoundError(f"Директория данных не найдена: {data_dir}")
            call_command(
                "import_catalog_from_1c",
                "--data-dir",
                str(data_dir),
                "--file-type",
                "all",
            )
            return {"type": "catalog", "message": "Каталог импортирован"}

        elif import_type == "stocks":
            file_path = data_path / "rests" / "rests.xml"
            if not file_path.exists():
                raise FileNotFoundError(
                    f"Файл остатков не найден: {file_path}. "
                    f"Убедитесь, что данные из 1С выгружены в {data_dir}"
                )
            call_command("load_product_stocks", "--file", str(file_path))
            return {"type": "stocks", "message": "Остатки обновлены"}

        elif import_type == "prices":
            if not data_path.exists():
                raise FileNotFoundError(f"Директория данных не найдена: {data_dir}")
            call_command(
                "import_catalog_from_1c",
                "--data-dir",
                str(data_dir),
                "--file-type",
                "prices",
            )
            return {"type": "prices", "message": "Цены обновлены"}

        elif import_type == "customers":
            # Ищем любой файл contragents в директории
            contragents_dir = data_path / "contragents"
            if not contragents_dir.exists():
                raise FileNotFoundError(
                    f"Директория контрагентов не найдена: {contragents_dir}"
                )

            # Ищем первый XML файл с контрагентами
            contragents_files = list(contragents_dir.glob("contragents*.xml"))
            if not contragents_files:
                raise FileNotFoundError(
                    f"Файлы контрагентов не найдены в {contragents_dir}. "
                    f"Убедитесь, что данные из 1С выгружены."
                )

            # Используем первый найденный файл
            file_path = contragents_files[0]
            call_command("import_customers_from_1c", "--file", str(file_path))
            return {"type": "customers", "message": "Клиенты импортированы"}

        else:
            raise ValueError(f"Неизвестный тип импорта: {import_type}")

    def _format_import_summary(self, results: list[dict[str, str]]) -> str:
        """
        Форматирование сводки результатов импорта.

        Args:
            results: Список результатов импорта

        Returns:
            Строка с форматированной сводкой
        """
        if not results:
            return "Импорт завершен (0 операций)"

        messages = [r["message"] for r in results]
        return f"Импорт завершен: {', '.join(messages)}"

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
