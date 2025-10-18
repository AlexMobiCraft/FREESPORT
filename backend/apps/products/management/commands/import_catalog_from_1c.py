"""
Management команда для импорта каталога товаров из 1С
"""
import os
from pathlib import Path
from typing import cast

from django.core.management.base import BaseCommand, CommandError

from apps.products.models import ImportSession
from apps.products.services.parser import XMLDataParser
from apps.products.services.processor import ProductDataProcessor


class Command(BaseCommand):
    """
    Импорт каталога товаров из XML файлов 1С (CommerceML 3.1)

    Использование:
        python manage.py import_catalog_from_1c --data-dir /path/to/1c/data
        python manage.py import_catalog_from_1c --data-dir /path --dry-run
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

    def handle(self, *args, **options):
        """Основная логика команды"""
        data_dir = options["data_dir"]
        dry_run = options.get("dry_run", False)

        # Валидация директории
        if not os.path.exists(data_dir):
            raise CommandError(f"Директория не найдена: {data_dir}")

        if not os.path.isdir(data_dir):
            raise CommandError(f"Путь не является директорией: {data_dir}")

        # Валидация структуры директории
        required_subdirs = ["goods", "offers", "prices", "rests", "priceLists"]
        for subdir in required_subdirs:
            subdir_path = os.path.join(data_dir, subdir)
            if not os.path.exists(subdir_path):
                raise CommandError(f"Отсутствует обязательная поддиректория: {subdir}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN MODE: Изменения не будут сохранены в БД")
            )
            return self._dry_run_import(data_dir)

        # Создание сессии импорта
        session = ImportSession.objects.create(
            import_type=ImportSession.ImportType.CATALOG,
            status=ImportSession.ImportStatus.STARTED,
        )
        session_id = cast(int, session.pk)

        self.stdout.write(
            self.style.SUCCESS(
                "✅ Создана сессия импорта ID: {session_id}".format(
                    session_id=session_id
                )
            )
        )

        try:
            # Инициализация парсера и процессора
            parser = XMLDataParser()
            processor = ProductDataProcessor(session_id=session_id)

            # ШАГ 1: Загрузка типов цен из priceLists*.xml
            self.stdout.write("\n📋 Шаг 1: Загрузка типов цен...")
            price_list_files = self._collect_xml_files(
                data_dir, "priceLists", "priceLists.xml"
            )
            if price_list_files:
                total_price_types = 0
                for file_path in price_list_files:
                    price_types_data = parser.parse_price_lists_xml(file_path)
                    processed = processor.process_price_types(price_types_data)
                    total_price_types += processed
                    self.stdout.write(
                        f"   • {Path(file_path).name}: типов цен {processed}"
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
            self.stdout.write("\n📦 Шаг 2: Создание заготовок товаров из goods.xml...")
            goods_files = self._collect_xml_files(data_dir, "goods", "goods.xml")
            if not goods_files:
                raise CommandError("Файлы goods.xml или goods_*.xml не найдены")

            for file_path in goods_files:
                goods_data = parser.parse_goods_xml(file_path)
                for goods_item in goods_data:
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
            self.stdout.write("\n🎁 Шаг 3: Обогащение товаров из offers.xml...")
            offers_files = self._collect_xml_files(data_dir, "offers", "offers.xml")
            if not offers_files:
                raise CommandError("Файлы offers.xml или offers_*.xml не найдены")

            for file_path in offers_files:
                offers_data = parser.parse_offers_xml(file_path)
                for offer_item in offers_data:
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
                    for price_item in prices_data:
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
                    for rest_item in rests_data:
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
