"""
Django management команда для импорта клиентов из 1С

Пример использования:
    python manage.py import_customers_from_1c --file=customers.xml
    python manage.py import_customers_from_1c --file=customers.json --dry-run
    python manage.py import_customers_from_1c --mock-data --chunk-size=50
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from tqdm import tqdm

from apps.users.models import User


class Command(BaseCommand):
    """
    Команда импорта клиентов из 1С (заглушка для будущей интеграции)
    """

    help = "Импорт клиентов из 1С (XML/JSON) - заглушка"

    def add_arguments(self, parser):
        """Добавление аргументов команды"""
        parser.add_argument(
            "--file", type=str, help="Путь к файлу данных 1С (XML или JSON)"
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Тестовый запуск без сохранения данных",
        )

        parser.add_argument(
            "--chunk-size",
            type=int,
            default=30,
            help="Размер батча для обработки клиентов (по умолчанию: 30)",
        )

        parser.add_argument(
            "--mock-data",
            action="store_true",
            help="Использовать встроенные тестовые данные вместо файла",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Принудительно перезаписать существующих клиентов",
        )

    def handle(self, *args, **options):
        """Основная логика команды"""

        self.dry_run = options["dry_run"]
        self.chunk_size = options["chunk_size"]
        self.force = options["force"]
        self.file_path = options["file"]
        self.use_mock_data = options["mock_data"]

        # Валидация параметров
        if not self.file_path and not self.use_mock_data:
            raise CommandError(
                (
                    "Укажите либо --file для загрузки из файла, "
                    "либо --mock-data для тестовых данных"
                )
            )

        # Заголовок
        self.stdout.write(self.style.SUCCESS("🚀 Запуск импорта клиентов из 1С"))
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("⚠️  РЕЖИМ DRY-RUN: изменения НЕ будут " "сохранены")
            )

        try:
            # Получение данных
            if self.use_mock_data:
                customers_data = self._get_mock_customers_data()
                self.stdout.write(
                    f"📦 Загружены тестовые данные: " f"{len(customers_data)} клиентов"
                )
            else:
                customers_data = self._load_data_from_file()
                self.stdout.write(f"📁 Загружен файл: {len(customers_data)} клиентов")

            # Импорт данных
            imported_count = self._import_customers(customers_data)

            # Финальная статистика
            if self.dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ DRY-RUN завершен: {imported_count} " f"клиентов обработано"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Импорт завершен успешно: {imported_count} "
                        f"клиентов импортировано"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка импорта: {str(e)}"))
            raise

    def _load_data_from_file(self) -> List[Dict]:
        """Загрузка данных из файла"""

        if not Path(self.file_path).exists():
            raise CommandError(f"Файл не найден: {self.file_path}")

        file_path = Path(self.file_path)

        if file_path.suffix.lower() == ".json":
            return self._parse_json_file(file_path)
        elif file_path.suffix.lower() in [".xml"]:
            return self._parse_xml_file(file_path)
        else:
            raise CommandError(
                f"Неподдерживаемый формат файла: {file_path.suffix}. "
                "Поддерживаются: .json, .xml"
            )

    def _parse_json_file(self, file_path: Path) -> List[Dict]:
        """Парсинг JSON файла"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict) and "customers" in data:
                customers_data = data["customers"]
                if isinstance(customers_data, list):
                    return customers_data
                return []
            elif isinstance(data, list):
                return data
            else:
                raise CommandError("Неверная структура JSON файла")

        except json.JSONDecodeError as e:
            raise CommandError(f"Ошибка парсинга JSON: {str(e)}")

    def _parse_xml_file(self, file_path: Path) -> List[Dict]:
        """Парсинг XML файла (заглушка)"""
        # TODO: Реализовать XML парсер после получения образцов от 1С
        raise CommandError(
            "XML парсер будет реализован после получения образцов "
            "файлов от 1С. Используйте --mock-data для тестирования."
        )

    def _get_mock_customers_data(self) -> List[Dict]:
        """Генерация тестовых данных клиентов"""

        mock_roles = [
            "retail",
            "wholesale_level1",
            "wholesale_level2",
            "wholesale_level3",
            "trainer",
        ]
        mock_companies = [
            "Спорт Маркет ООО",
            "Атлет Спорт",
            "Фитнес Клуб Энергия",
            "Спортивная База",
            "Олимп Спорт",
            "Динамо Снаб",
            "Чемпион Трейд",
        ]

        customers = []

        for i in range(1, 16):  # 15 тестовых клиентов
            customer = {
                "onec_id": f"1C-CUSTOMER-{i:05d}",
                "email": f"customer{i}@test-1c.ru",
                "first_name": f"Имя{i}",
                "last_name": f"Фамилия{i}",
                "role": mock_roles[i % len(mock_roles)],
                "is_active": i % 8 != 0,  # 87% активных клиентов
                "phone_number": f"+7{900 + i % 99}{1000000 + i * 123:07d}",
                "company_name": mock_companies[i % len(mock_companies)]
                if i % 3 == 0
                else "",
                "tax_id": f"{7000000000 + i * 123456}" if i % 3 == 0 else "",
                "address": f"г. Москва, ул. Тестовая, д. {i}",
                "created_in_1c": True,
                "sync_status": "synced" if i % 6 != 0 else "pending",
            }
            customers.append(customer)

        return customers

    def _import_customers(self, customers_data: List[Dict]) -> int:
        """Импорт клиентов в базу данных"""

        imported_count = 0

        # Progress bar
        progress_bar = tqdm(
            customers_data,
            desc="Импорт клиентов",
            unit="клиентов",
            ncols=100,
            leave=True,
        )

        with transaction.atomic():
            if self.dry_run:
                # Создаем savepoint для rollback в dry-run режиме
                savepoint = transaction.savepoint()

            try:
                # Обработка клиентов по батчам
                for i in range(0, len(customers_data), self.chunk_size):
                    chunk = customers_data[i : i + self.chunk_size]
                    imported_count += self._process_customers_chunk(chunk, progress_bar)

                if self.dry_run:
                    # Rollback изменений в dry-run режиме
                    transaction.savepoint_rollback(savepoint)

            except Exception:
                if not self.dry_run:
                    raise
                else:
                    transaction.savepoint_rollback(savepoint)
                    raise

        progress_bar.close()
        return imported_count

    def _process_customers_chunk(self, chunk: List[Dict], progress_bar: Any) -> int:
        """Обработка батча клиентов"""

        processed_count = 0

        for customer_data in chunk:
            try:
                # Обработка одного клиента
                self._process_single_customer(customer_data)
                processed_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ Ошибка обработки клиента "
                        f'{customer_data.get("onec_id", "UNKNOWN")}: {e}'
                    )
                )
                if not self.force:
                    raise

            # Обновление progress bar
            progress_bar.update(1)

            # Небольшая задержка для демонстрации
            if self.use_mock_data:
                time.sleep(0.01)

        return processed_count

    def _process_single_customer(self, customer_data: Dict) -> None:
        """Обработка одного клиента"""

        onec_id = customer_data.get("onec_id")
        if not onec_id:
            raise ValueError("Отсутствует onec_id клиента")

        # Данные клиента (маппинг полей на поля модели User)
        customer_defaults = {
            "email": customer_data.get("email", ""),
            "first_name": customer_data.get("first_name", ""),
            "last_name": customer_data.get("last_name", ""),
            "phone": customer_data.get("phone_number", ""),
            "role": customer_data.get("role", "retail"),
            "is_active": customer_data.get("is_active", True),
            "company_name": customer_data.get("company_name", ""),
            "tax_id": customer_data.get("tax_id", ""),
            # address поле не существует в User модели - игнорируем
            "created_in_1c": customer_data.get("created_in_1c", True),
            "sync_status": customer_data.get("sync_status", "synced"),
            "last_sync_at": timezone.now(),
            "sync_error_message": "",
        }

        # Создание или обновление клиента
        if self.force:
            # Для update_or_create нужно отдельно обрабатывать пароль
            # при создании
            try:
                customer = User.objects.get(onec_id=onec_id)
                # Обновляем существующего
                for key, value in customer_defaults.items():
                    setattr(customer, key, value)
                customer.save()
                action = "обновлен"
            except User.DoesNotExist:
                # Создаем нового с паролем
                customer = User.objects.create_user(
                    password="temp_password_1c_sync",
                    onec_id=onec_id,
                    **customer_defaults,
                )
                action = "создан"
        else:
            # Проверяем существование клиента перед созданием
            if User.objects.filter(onec_id=onec_id).exists():
                if not self.dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  Клиент {onec_id} уже существует, " f"пропускаем"
                        )
                    )
                return
            elif User.objects.filter(email=customer_defaults["email"]).exists():
                if not self.dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  Клиент с email "
                            f"{customer_defaults['email']} уже существует, "
                            f"пропускаем"
                        )
                    )
                return
            else:
                customer = User.objects.create_user(
                    password="temp_password_1c_sync",
                    onec_id=onec_id,
                    **customer_defaults,
                )
                action = "создан"

        # Логирование (только в verbose режиме)
        if getattr(self, "verbosity", 1) >= 2:
            self.stdout.write(
                f"✅ Клиент {onec_id} ({customer.first_name} "
                f"{customer.last_name}) {action}"
            )
