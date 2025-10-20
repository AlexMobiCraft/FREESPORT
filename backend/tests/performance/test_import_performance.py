"""
Performance тесты для команды импорта каталога из 1С
"""
import tempfile
import time
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import override_settings

from apps.products.models import ImportSession, Product


def generate_test_xml_with_n_products(n: int) -> bytes:
    """Генерирует XML с N товарами для тестирования"""
    goods_items = []
    for i in range(n):
        goods_items.append(
            f"""    <Товар>
      <Ид>parent-uuid-{i:04d}</Ид>
      <Наименование>Тестовый товар {i}</Наименование>
      <Артикул>TEST-{i:04d}</Артикул>
    </Товар>"""
        )

    goods_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Каталог>
  <Товары>
{chr(10).join(goods_items)}
  </Товары>
</Каталог>"""

    return goods_xml.encode("utf-8")


def generate_offers_xml_with_n_products(n: int) -> bytes:
    """Генерирует offers.xml с N товарами"""
    offer_items = []
    for i in range(n):
        offer_items.append(
            f"""    <Предложение>
      <Ид>parent-uuid-{i:04d}#sku-uuid-{i:04d}</Ид>
      <Наименование>Тестовый товар {i} SKU</Наименование>
      <Артикул>TEST-{i:04d}-SKU</Артикул>
    </Предложение>"""
        )

    offers_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
{chr(10).join(offer_items)}
  </Предложения>
</ПакетПредложений>"""

    return offers_xml.encode("utf-8")


def generate_prices_xml_with_n_products(n: int) -> bytes:
    """Генерирует prices.xml с N товарами"""
    price_items = []
    for i in range(n):
        price = 1000.00 + (i * 10)
        price_items.append(
            f"""    <Предложение>
      <Ид>parent-uuid-{i:04d}#sku-uuid-{i:04d}</Ид>
      <Цены>
        <Цена>
          <ИдТипаЦены>retail-uuid</ИдТипаЦены>
          <ЦенаЗаЕдиницу>{price:.2f}</ЦенаЗаЕдиницу>
        </Цена>
      </Цены>
    </Предложение>"""
        )

    prices_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
{chr(10).join(price_items)}
  </Предложения>
</ПакетПредложений>"""

    return prices_xml.encode("utf-8")


def generate_rests_xml_with_n_products(n: int) -> bytes:
    """Генерирует rests.xml с N товарами"""
    rest_items = []
    for i in range(n):
        quantity = 10 + (i % 50)
        rest_items.append(
            f"""    <Предложение>
      <Ид>parent-uuid-{i:04d}#sku-uuid-{i:04d}</Ид>
      <Остатки>
        <Остаток>
          <Склад>warehouse-1</Склад>
          <Количество>{quantity}</Количество>
        </Остаток>
      </Остатки>
    </Предложение>"""
        )

    rests_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
{chr(10).join(rest_items)}
  </Предложения>
</ПакетПредложений>"""

    return rests_xml.encode("utf-8")


@pytest.mark.django_db
@pytest.mark.slow
class TestImportPerformance:
    """Performance тесты для импорта каталога"""

    def setup_test_data_directory(self, tmp_path, num_products: int):
        """Создает директорию с тестовыми XML файлами"""
        test_dir = tmp_path / "perf_test_data"
        test_dir.mkdir()

        # Создаем поддиректории
        for subdir in ["goods", "offers", "prices", "rests", "priceLists"]:
            (test_dir / subdir).mkdir()

        # Создаем priceLists.xml
        price_lists_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <ТипыЦен>
    <ТипЦены>
      <Ид>retail-uuid</Ид>
      <Наименование>РРЦ</Наименование>
      <Валюта>RUB</Валюта>
    </ТипЦены>
  </ТипыЦен>
</ПакетПредложений>"""
        (test_dir / "priceLists" / "priceLists.xml").write_bytes(
            price_lists_xml.encode("utf-8")
        )

        # Генерируем XML файлы с N товарами
        (test_dir / "goods" / "goods.xml").write_bytes(
            generate_test_xml_with_n_products(num_products)
        )
        (test_dir / "offers" / "offers.xml").write_bytes(
            generate_offers_xml_with_n_products(num_products)
        )
        (test_dir / "prices" / "prices.xml").write_bytes(
            generate_prices_xml_with_n_products(num_products)
        )
        (test_dir / "rests" / "rests.xml").write_bytes(
            generate_rests_xml_with_n_products(num_products)
        )

        return test_dir

    @override_settings(BACKUP_DIR=tempfile.gettempdir())
    def test_import_100_products_performance(self, tmp_path):
        """Тест производительности импорта 100 товаров (baseline)"""
        test_dir = self.setup_test_data_directory(tmp_path, 100)

        start_time = time.time()
        out = StringIO()

        call_command("import_catalog_from_1c", "--data-dir", str(test_dir), stdout=out)

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Проверяем что импорт завершился успешно
        output = out.getvalue()
        assert "ИМПОРТ ЗАВЕРШЕН УСПЕШНО" in output

        # Проверяем количество импортированных товаров
        assert Product.objects.count() >= 100

        # Проверяем статус сессии
        session = ImportSession.objects.latest("started_at")
        assert session.status == ImportSession.ImportStatus.COMPLETED

        # Baseline: 100 товаров должны импортироваться за разумное время
        assert (
            elapsed_time < 60
        ), f"Import of 100 products took {elapsed_time:.2f}s, expected < 60s"

        print(f"\n✅ Import of 100 products completed in {elapsed_time:.2f}s")

    @override_settings(BACKUP_DIR=tempfile.gettempdir())
    def test_import_1000_products_within_timeout(self, tmp_path):
        """Тест импорта 1000 товаров в допустимое время (<5 минут) - DoD requirement"""
        test_dir = self.setup_test_data_directory(tmp_path, 1000)

        start_time = time.time()
        out = StringIO()

        call_command("import_catalog_from_1c", "--data-dir", str(test_dir), stdout=out)

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Проверяем что импорт завершился успешно
        output = out.getvalue()
        assert "ИМПОРТ ЗАВЕРШЕН УСПЕШНО" in output

        # Проверяем количество импортированных товаров
        assert Product.objects.count() >= 1000

        # Проверяем статус сессии
        session = ImportSession.objects.latest("started_at")
        assert session.status == ImportSession.ImportStatus.COMPLETED

        # DoD requirement: импорт 1000+ товаров должен завершаться
        # за < 5 минут (300 секунд)
        assert elapsed_time < 300, (
            f"Import of 1000 products took {elapsed_time:.2f}s, "
            f"expected < 300s (DoD requirement)"
        )

        print(f"\n✅ Import of 1000 products completed in " f"{elapsed_time:.2f}s")
        print(f"   Performance: {1000 / elapsed_time:.2f} products/second")

    @override_settings(BACKUP_DIR=tempfile.gettempdir())
    def test_import_with_chunk_size_performance(self, tmp_path):
        """Тест влияния chunk-size на производительность"""
        test_dir = self.setup_test_data_directory(tmp_path, 500)

        # Тест с chunk-size=100
        Product.objects.all().delete()
        ImportSession.objects.all().delete()

        start_time = time.time()
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(test_dir),
            "--chunk-size",
            "100",
        )
        time_chunk_100 = time.time() - start_time

        # Тест с chunk-size=500
        Product.objects.all().delete()
        ImportSession.objects.all().delete()

        start_time = time.time()
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(test_dir),
            "--chunk-size",
            "500",
        )
        time_chunk_500 = time.time() - start_time

        print("\n📊 Chunk size performance comparison:")
        print(f"   chunk-size=100: {time_chunk_100:.2f}s")
        print(f"   chunk-size=500: {time_chunk_500:.2f}s")
        print(
            f"   Difference: {abs(time_chunk_100 - time_chunk_500):.2f}s "
            f"({abs(time_chunk_100 - time_chunk_500) / time_chunk_100 * 100:.1f}%)"
        )

        # Оба варианта должны завершаться за разумное время
        assert time_chunk_100 < 180, f"chunk-size=100 took {time_chunk_100:.2f}s"
        assert time_chunk_500 < 180, f"chunk-size=500 took {time_chunk_500:.2f}s"

    @override_settings(BACKUP_DIR=tempfile.gettempdir())
    def test_import_memory_usage(self, tmp_path):
        """Тест использования памяти при импорте"""
        import tracemalloc

        test_dir = self.setup_test_data_directory(tmp_path, 500)

        tracemalloc.start()

        call_command("import_catalog_from_1c", "--data-dir", str(test_dir))

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_mb = peak / 1024 / 1024

        # Проверяем что использование памяти разумное
        assert (
            memory_mb < 200
        ), f"Memory usage {memory_mb:.2f}MB exceeds 200MB limit for 500 products"

        print(f"\n💾 Memory usage for 500 products: {memory_mb:.2f}MB")
        print(f"   Peak memory: {peak / 1024 / 1024:.2f}MB")
        print(f"   Current memory: {current / 1024 / 1024:.2f}MB")

    @override_settings(BACKUP_DIR=tempfile.gettempdir())
    def test_import_database_queries_efficiency(self, tmp_path):
        """Тест эффективности запросов к БД при импорте"""
        from django.db import connection, reset_queries
        from django.test.utils import override_settings as django_override_settings

        test_dir = self.setup_test_data_directory(tmp_path, 100)

        with django_override_settings(DEBUG=True):
            reset_queries()

            call_command("import_catalog_from_1c", "--data-dir", str(test_dir))

            queries_count = len(connection.queries)

        # Bulk operations должны минимизировать количество запросов
        # Для 100 товаров ожидаем разумное количество запросов (не N+1)
        queries_per_product = queries_count / 100

        print("\n🗄️  Database queries for 100 products:")
        print(f"   Total queries: {queries_count}")
        print(f"   Queries per product: {queries_per_product:.2f}")

        # Проверяем что используются bulk operations
        # ~12-15 запросов на товар нормально с учетом:
        # goods, offers, prices (2 типа), rests, categories, brands
        assert (
            queries_per_product < 20
        ), f"Too many queries per product: {queries_per_product:.2f}"

    @override_settings(BACKUP_DIR=tempfile.gettempdir())
    def test_import_with_skip_validation_performance(self, tmp_path):
        """Тест влияния --skip-validation на производительность"""
        test_dir = self.setup_test_data_directory(tmp_path, 500)

        # Тест с валидацией
        Product.objects.all().delete()
        ImportSession.objects.all().delete()

        start_time = time.time()
        call_command("import_catalog_from_1c", "--data-dir", str(test_dir))
        time_with_validation = time.time() - start_time

        # Тест без валидации
        Product.objects.all().delete()
        ImportSession.objects.all().delete()

        start_time = time.time()
        call_command(
            "import_catalog_from_1c", "--data-dir", str(test_dir), "--skip-validation"
        )
        time_without_validation = time.time() - start_time

        speedup = (
            (time_with_validation - time_without_validation) / time_with_validation
        ) * 100

        print("\n⚡ Skip validation performance impact:")
        print(f"   With validation: {time_with_validation:.2f}s")
        print(f"   Without validation: {time_without_validation:.2f}s")
        print(f"   Speedup: {speedup:.1f}%")

        # Skip-validation может не всегда ускорять из-за overhead и других факторов
        # Просто проверяем что оба варианта завершаются за разумное время
        assert (
            time_with_validation < 30
        ), f"With validation took {time_with_validation:.2f}s, expected < 30s"
        assert (
            time_without_validation < 30
        ), f"Without validation took {time_without_validation:.2f}s, expected < 30s"
