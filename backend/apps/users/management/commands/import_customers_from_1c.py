"""
Django management команда для импорта клиентов из файла 1С (contragents.xml)
"""
from __future__ import annotations

import logging
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.common.models import CustomerSyncLog
from apps.products.models import ImportSession
from apps.users.models import User
from apps.users.services.parser import CustomerDataParser
from apps.users.services.processor import CustomerDataProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Импортирует клиентов из файла 1С (contragents.xml).

    Использует архитектуру Парсер/Процессор для гибкости.
    Создает ImportSession для отслеживания импорта.
    Логирует детали операций в CustomerSyncLog.
    """

    help = "Импортирует клиентов из файла 1С (contragents.xml)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Путь к файлу contragents.xml.",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=100,
            help="Размер пакета для обработки (по умолчанию: 100).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Тестовый запуск без сохранения данных.",
        )

    def handle(self, *args, **options) -> None:
        file_path = options["file"]
        chunk_size = options["chunk_size"]
        dry_run = options["dry_run"]

        # Валидация входных данных
        if not os.path.exists(file_path):
            raise CommandError(f"Файл не найден: {file_path}")

        if chunk_size <= 0:
            raise CommandError("chunk-size должен быть положительным числом.")

        # Проверка на активные сессии импорта (Concurrent Execution Protection)
        active_sessions = ImportSession.objects.filter(
            import_type=ImportSession.ImportType.CUSTOMERS,
            status=ImportSession.ImportStatus.STARTED,
        ).exists()

        if active_sessions:
            raise CommandError(
                "Импорт клиентов уже выполняется. "
                "Дождитесь завершения или отмените активную сессию."
            )

        session = None  # Initialize session variable
        try:
            with transaction.atomic():
                # Создание сессии импорта внутри транзакции для поддержки dry-run
                session = ImportSession.objects.create(
                    import_type=ImportSession.ImportType.CUSTOMERS,
                    status=ImportSession.ImportStatus.STARTED,
                )

                self.stdout.write(
                    self.style.SUCCESS(f"Начата сессия импорта #{session.pk}")
                )
                # Парсинг данных из XML
                self.stdout.write("Парсинг файла...")
                parser = CustomerDataParser()
                customer_data = parser.parse(file_path)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Распознано {len(customer_data)} клиентов"
                    )
                )

                # Обработка данных
                self.stdout.write("Обработка клиентов...")
                processor = CustomerDataProcessor(session_id=session.pk)
                result = processor.process_customers(
                    customer_data, chunk_size=chunk_size
                )

                # Вывод статистики
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nСтатистика обработки:\n"
                        f"  Всего: {result['total']}\n"
                        f"  Создано: {result['created']}\n"
                        f"  Обновлено: {result['updated']}\n"
                        f"  Пропущено: {result['skipped']}\n"
                        f"  Ошибок: {result['errors']}"
                    )
                )

                # Dry-run режим
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            "\n⚠️  DRY-RUN режим: изменения не сохранены"
                        )
                    )
                    transaction.set_rollback(True)
                else:
                    # Обновление сессии
                    session.status = ImportSession.ImportStatus.COMPLETED
                    session.report_details = result
                    session.finished_at = timezone.now()
                    session.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"\n✅ Импорт завершен успешно. Сессия #{session.pk}"
                        )
                    )

        except Exception as e:
            # Обработка ошибок
            if session:
                session.status = ImportSession.ImportStatus.FAILED
                session.error_message = str(e)
                session.finished_at = timezone.now()
                session.save()

                self.stdout.write(
                    self.style.ERROR(
                        f"\n❌ Ошибка импорта: {str(e)}\n"
                        f"Сессия #{session.pk} завершена с ошибкой"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"\n❌ Ошибка импорта: {str(e)}")
                )

            logger.error(f"Ошибка импорта клиентов: {e}", exc_info=True)
            raise CommandError(f"Импорт завершен с ошибкой: {e}") from e
