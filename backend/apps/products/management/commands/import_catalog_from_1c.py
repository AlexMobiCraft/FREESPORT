"""
Management команда для импорта каталога товаров из 1С
"""
import os
from pathlib import Path
from typing import cast

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from tqdm import tqdm

from apps.products.models import Brand, Category, ImportSession, Product
from apps.products.services.parser import XMLDataParser
from apps.products.services.processor import ProductDataProcessor


class Command(BaseCommand):
    """
    Импорт каталога товаров из XML файлов 1С (CommerceML 3.1)

    Использование:
        python manage.py import_catalog_from_1c --data-dir /path/to/1c/data
        python manage.py import_catalog_from_1c --data-dir /path --dry-run
        python manage.py import_catalog_from_1c --data-dir /path --chunk-size=500
        python manage.py import_catalog_from_1c --data-dir /path --file-type=goods
        python manage.py import_catalog_from_1c --data-dir /path --clear-existing
    """

    help = "Импорт каталога товаров из файлов 1С (CommerceML 3.1)"

    def add_arguments(self, parser):
        """Добавление аргументов команды"""
        parser.add_argument(
            "--data-dir",
            type=str,
            required=True,
            help="Путь к директории с XML файлами из 1С",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Тестовый запуск без записи в БД",
        )
        # Story 3.1.2: Расширенные параметры
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=1000,
            help="Размер пакета для bulk операций (default: 1000)",
        )
        parser.add_argument(
            "--skip-validation",
            action="store_true",
            help="Пропустить валидацию данных для ускорения импорта",
        )
        parser.add_argument(
            "--file-type",
            type=str,
            choices=["goods", "offers", "prices", "rests", "all"],
            default="all",
            help="Выборочный импорт конкретного типа файлов (default: all)",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help=(
                "Очистить существующие данные перед импортом "
                "(ВНИМАНИЕ: удалит все товары)"
            ),
        )
        parser.add_argument(
            "--skip-backup",
            action="store_true",
            help="Пропустить создание backup перед импортом",
        )

    def handle(self, *args, **options):
        """Основная логика команды"""
        data_dir = options["data_dir"]
        dry_run = options.get("dry_run", False)
        chunk_size = options.get("chunk_size", 1000)
        skip_validation = options.get("skip_validation", False)
        file_type = options.get("file_type", "all")
        clear_existing = options.get("clear_existing", False)
        skip_backup = options.get("skip_backup", False)

        # Валидация директории
        if not os.path.exists(data_dir):
            raise CommandError(f"Директория не найдена: {data_dir}")

        if not os.path.isdir(data_dir):
            raise CommandError(f"Путь не является директорией: {data_dir}")

        # Валидация структуры директории (только если нужны все файлы)
        if file_type == "all":
            required_subdirs = ["goods", "offers", "prices", "rests", "priceLists"]
            for subdir in required_subdirs:
                subdir_path = os.path.join(data_dir, subdir)
                if not os.path.exists(subdir_path):
                    raise CommandError(
                        f"Отсутствует обязательная поддиректория: {subdir}"
                    )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN MODE: Изменения не будут сохранены в БД")
            )
            return self._dry_run_import(data_dir)

        # Story 3.1.2: Автоматический backup перед полным импортом
        if not dry_run and file_type == "all" and not skip_backup:
            self.stdout.write(
                self.style.WARNING("\n💾 Создание backup перед импортом...")
            )
            try:
                call_command("backup_db")
                self.stdout.write(self.style.SUCCESS("✅ Backup создан успешно"))
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️ Не удалось создать backup: {e}. Продолжаем импорт..."
                    )
                )

        # Story 3.1.2: Очистка существующих данных
        if clear_existing:
            self.stdout.write(
                self.style.WARNING(
                    (
                        "\n⚠️ ВНИМАНИЕ: Удаление всех существующих товаров, "
                        "категорий и брендов..."
                    )
                )
            )
            confirm = input("Вы уверены? Введите 'yes' для подтверждения: ")
            if confirm.lower() == "yes":
                Product.objects.all().delete()
                Category.objects.all().delete()
                Brand.objects.all().delete()
                self.stdout.write(self.style.SUCCESS("✅ Данные очищены"))
            else:
                self.stdout.write(self.style.ERROR("❌ Очистка отменена"))
                return

        # Вывод параметров импорта
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📊 ПАРАМЕТРЫ ИМПОРТА:")
        self.stdout.write(f"   Директория: {data_dir}")
        self.stdout.write(f"   Тип файлов: {file_type}")
        self.stdout.write(f"   Chunk size: {chunk_size}")
        self.stdout.write(f"   Skip validation: {skip_validation}")
        self.stdout.write(f"   Skip backup: {skip_backup}")
        self.stdout.write(f"   Clear existing: {clear_existing}")
        self.stdout.write("=" * 50)

        # Создание сессии импорта
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )
        session_id = cast(int, session.pk)

        self.stdout.write(
            self.style.SUCCESS(
                "\n✅ Создана сессия импорта ID: {session_id}".format(
                    session_id=session_id
                )
            )
        )

        try:
            # Инициализация парсера и процессора с параметрами
            parser = XMLDataParser()
            processor = ProductDataProcessor(
                session_id=session_id,
                skip_validation=skip_validation,
                chunk_size=chunk_size,
            )

            # ШАГ 0.5: Загрузка категорий из groups.xml (Story 3.1.2)
            if file_type in ["all", "goods"]:
                self.stdout.write("\n📁 Шаг 0.5: Загрузка категорий...")
                groups_files = self._collect_xml_files(data_dir, "groups", "groups.xml")
                if groups_files:
                    total_categories = 0
                    for file_path in groups_files:
                        categories_data = parser.parse_groups_xml(file_path)
                        # Story 3.1.2: Добавлен прогресс-бар
                        result = processor.process_categories(categories_data)
                        total_categories += result["created"] + result["updated"]
                        self.stdout.write(
                            (
                                f"   • {Path(file_path).name}: "
                                f"категорий {len(categories_data)}"
                            )
                        )
                        if result["cycles_detected"] > 0:
                            self.stdout.write(
                                self.style.WARNING(
                                    (
                                        "   ⚠️ Обнаружено циклических ссылок: "
                                        f"{result['cycles_detected']}"
                                    )
                                )
                            )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"   ✅ Загружено категорий (всего): {total_categories}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING("   ⚠️ Файлы groups.xml не найдены")
                    )

            # ШАГ 0.6: Загрузка брендов из propertiesGoods.xml
            if file_type in ["all", "goods"]:
                self.stdout.write("\n🏷️  Шаг 0.6: Загрузка брендов...")
                properties_goods_files = self._collect_xml_files(
                    data_dir, "propertiesGoods", "propertiesGoods.xml"
                )
                if properties_goods_files:
                    total_brands = 0
                    for file_path in properties_goods_files:
                        brands_data = parser.parse_properties_goods_xml(file_path)
                        result = processor.process_brands(brands_data)
                        total_brands += result["created"] + result["updated"]
                        self.stdout.write(
                            (
                                f"   • {Path(file_path).name}: "
                                f"брендов {len(brands_data)}"
                            )
                        )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"   ✅ Загружено брендов (всего): {total_brands}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING("   ⚠️ Файлы propertiesGoods*.xml не найдены")
                    )

            # ШАГ 1: Загрузка типов цен из priceLists*.xml
            if file_type in ["all", "prices"]:
                self.stdout.write("\n📋 Шаг 1: Загрузка типов цен...")
                price_list_files = self._collect_xml_files(
                    data_dir, "priceLists", "priceLists.xml"
                )
                if price_list_files:
                    total_price_types = 0
                    for file_path in price_list_files:
                        price_types_data = parser.parse_price_lists_xml(file_path)
                        # Story 3.1.2: Добавлен прогресс-бар
                        for price_type in tqdm(
                            price_types_data,
                            desc=f"   Обработка {Path(file_path).name}",
                            disable=len(price_types_data) < 10,
                        ):
                            processor.process_price_types([price_type])
                        total_price_types += len(price_types_data)
                        self.stdout.write(
                            (
                                f"   • {Path(file_path).name}: "
                                f"типов цен {len(price_types_data)}"
                            )
                        )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"   ✅ Загружено типов цен (всего): {total_price_types}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING("   ⚠️ Файлы priceLists*.xml не найдены")
                    )

            # ШАГ 2: Парсинг goods*.xml - создание заготовок товаров
            if file_type in ["all", "goods"]:
                self.stdout.write(
                    "\n📦 Шаг 2: Создание заготовок товаров из goods.xml..."
                )
                goods_files = self._collect_xml_files(data_dir, "goods", "goods.xml")
                if not goods_files and file_type == "all":
                    raise CommandError("Файлы goods.xml или goods_*.xml не найдены")

                for file_path in goods_files:
                    goods_data = parser.parse_goods_xml(file_path)
                    # Story 3.1.2: Добавлен прогресс-бар
                    for goods_item in tqdm(
                        goods_data, desc=f"   Обработка {Path(file_path).name}"
                    ):
                        processor.create_product_placeholder(goods_item)
                    self.stdout.write(
                        f"   • {Path(file_path).name}: товаров {len(goods_data)}"
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"   ✅ Создано заготовок: {processor.stats['created']}"
                    )
                )

            # ШАГ 3: Парсинг offers*.xml - обогащение товаров
            if file_type in ["all", "offers"]:
                self.stdout.write("\n🎁 Шаг 3: Обогащение товаров из offers.xml...")
                offers_files = self._collect_xml_files(data_dir, "offers", "offers.xml")
                if not offers_files and file_type == "all":
                    raise CommandError("Файлы offers.xml или offers_*.xml не найдены")

                for file_path in offers_files:
                    offers_data = parser.parse_offers_xml(file_path)
                    # Story 3.1.2: Добавлен прогресс-бар
                    for offer_item in tqdm(
                        offers_data, desc=f"   Обработка {Path(file_path).name}"
                    ):
                        processor.enrich_product_from_offer(offer_item)
                    self.stdout.write(
                        f"   • {Path(file_path).name}: предложений {len(offers_data)}"
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"   ✅ Обогащено товаров: {processor.stats['updated']}"
                    )
                )

            # ШАГ 4: Парсинг prices*.xml - обновление цен
            if file_type in ["all", "prices"]:
                self.stdout.write("\n💰 Шаг 4: Обновление цен из prices.xml...")
                prices_files = self._collect_xml_files(data_dir, "prices", "prices.xml")
                if not prices_files:
                    self.stdout.write(
                        self.style.WARNING(
                            "   ⚠️ Файлы prices.xml или prices_*.xml не найдены"
                        )
                    )
                else:
                    for file_path in prices_files:
                        prices_data = parser.parse_prices_xml(file_path)
                        # Story 3.1.2: Добавлен прогресс-бар
                        for price_item in tqdm(
                            prices_data, desc=f"   Обработка {Path(file_path).name}"
                        ):
                            processor.update_product_prices(price_item)
                        self.stdout.write(
                            "   • {name}: записей цен {count}".format(
                                name=Path(file_path).name, count=len(prices_data)
                            )
                        )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"   ✅ Обновлено цен: {processor.stats['updated']}"
                        )
                    )

            # ШАГ 5: Парсинг rests*.xml - обновление остатков
            if file_type in ["all", "rests"]:
                self.stdout.write("\n📊 Шаг 5: Обновление остатков из rests.xml...")
                rests_files = self._collect_xml_files(data_dir, "rests", "rests.xml")
                if not rests_files:
                    self.stdout.write(
                        self.style.WARNING(
                            "   ⚠️ Файлы rests.xml или rests_*.xml не найдены"
                        )
                    )
                else:
                    for file_path in rests_files:
                        rests_data = parser.parse_rests_xml(file_path)
                        # Story 3.1.2: Добавлен прогресс-бар
                        for rest_item in tqdm(
                            rests_data, desc=f"   Обработка {Path(file_path).name}"
                        ):
                            processor.update_product_stock(rest_item)
                        self.stdout.write(
                            "   • {name}: записей остатков {count}".format(
                                name=Path(file_path).name, count=len(rests_data)
                            )
                        )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"   ✅ Обновлено остатков: {processor.stats['updated']}"
                        )
                    )

            # Финализация сессии
            processor.finalize_session(status=ImportSession.ImportStatus.COMPLETED)

            # Вывод статистики
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(self.style.SUCCESS("✅ ИМПОРТ ЗАВЕРШЕН УСПЕШНО"))
            self.stdout.write("=" * 50)
            self.stdout.write(f"Создано товаров:   {processor.stats['created']}")
            self.stdout.write(f"Обновлено товаров: {processor.stats['updated']}")
            self.stdout.write(f"Пропущено:         {processor.stats['skipped']}")
            self.stdout.write(f"Ошибок:            {processor.stats['errors']}")
            self.stdout.write("=" * 50)

        except Exception as e:
            # Обработка ошибок
            self.stdout.write(self.style.ERROR(f"\n❌ ОШИБКА ИМПОРТА: {e}"))

            # Обновление статуса сессии
            session.status = ImportSession.ImportStatus.FAILED
            session.error_message = str(e)
            session.save()

            raise CommandError(f"Импорт завершился с ошибкой: {e}")

    def _collect_xml_files(
        self, base_dir: str, subdir: str, filename: str
    ) -> list[str]:
        """
        Возвращает упорядоченный список XML файлов,
        включая сегментированные выгрузки.
        """

        base_path = Path(base_dir) / subdir
        if not base_path.exists():
            return []

        collected: list[Path] = []
        prefix = filename.replace(".xml", "")

        direct_file = base_path / filename
        if direct_file.exists():
            collected.append(direct_file)

        for segmented_file in sorted(base_path.glob(f"{prefix}_*.xml")):
            if segmented_file not in collected:
                collected.append(segmented_file)

        legacy_file = base_path / "import_files" / filename
        if legacy_file.exists() and legacy_file not in collected:
            collected.append(legacy_file)

        return [str(path) for path in collected]

    def _dry_run_import(self, data_dir: str) -> None:
        """Тестовый запуск импорта без записи в БД"""
        parser = XMLDataParser()

        self.stdout.write("\n📋 Проверка priceLists.xml...")
        price_list_files = self._collect_xml_files(
            data_dir, "priceLists", "priceLists.xml"
        )
        if price_list_files:
            total_price_types = 0
            for file_path in price_list_files:
                price_types = parser.parse_price_lists_xml(file_path)
                total_price_types += len(price_types)
                self.stdout.write(
                    f"   • {Path(file_path).name}: записей {len(price_types)}"
                )
            self.stdout.write(f"   ✅ Найдено типов цен (всего): {total_price_types}")
        else:
            self.stdout.write("   ⚠️ Файлы не найдены")

        self.stdout.write("\n📦 Проверка goods.xml...")
        goods_files = self._collect_xml_files(data_dir, "goods", "goods.xml")
        if goods_files:
            total_goods = 0
            for file_path in goods_files:
                goods_data = parser.parse_goods_xml(file_path)
                total_goods += len(goods_data)
                self.stdout.write(
                    f"   • {Path(file_path).name}: товаров {len(goods_data)}"
                )
            self.stdout.write(f"   ✅ Найдено товаров (всего): {total_goods}")
        else:
            self.stdout.write("   ❌ Файлы не найдены")

        self.stdout.write("\n🎁 Проверка offers.xml...")
        offers_files = self._collect_xml_files(data_dir, "offers", "offers.xml")
        if offers_files:
            total_offers = 0
            for file_path in offers_files:
                offers_data = parser.parse_offers_xml(file_path)
                total_offers += len(offers_data)
                self.stdout.write(
                    f"   • {Path(file_path).name}: предложений {len(offers_data)}"
                )
            self.stdout.write(f"   ✅ Найдено предложений (всего): {total_offers}")
        else:
            self.stdout.write("   ❌ Файлы не найдены")

        self.stdout.write("\n💰 Проверка prices.xml...")
        prices_files = self._collect_xml_files(data_dir, "prices", "prices.xml")
        if prices_files:
            total_prices = 0
            for file_path in prices_files:
                prices_data = parser.parse_prices_xml(file_path)
                total_prices += len(prices_data)
                self.stdout.write(
                    f"   • {Path(file_path).name}: записей цен {len(prices_data)}"
                )
            self.stdout.write(f"   ✅ Найдено записей цен (всего): {total_prices}")
        else:
            self.stdout.write("   ⚠️ Файлы не найдены")

        self.stdout.write("\n📊 Проверка rests.xml...")
        rests_files = self._collect_xml_files(data_dir, "rests", "rests.xml")
        if rests_files:
            total_rests = 0
            for file_path in rests_files:
                rests_data = parser.parse_rests_xml(file_path)
                total_rests += len(rests_data)
                self.stdout.write(
                    f"   • {Path(file_path).name}: записей остатков {len(rests_data)}"
                )
            self.stdout.write(f"   ✅ Найдено записей остатков (всего): {total_rests}")
        else:
            self.stdout.write("   ⚠️ Файлы не найдены")

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(
            self.style.SUCCESS("✅ DRY RUN ЗАВЕРШЕН: Структура файлов корректна")
        )
        self.stdout.write("=" * 50)
