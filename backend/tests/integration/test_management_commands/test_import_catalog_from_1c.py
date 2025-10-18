"""
Интеграционные тесты для команды import_catalog_from_1c
"""
import os
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.products.models import ImportSession, Product


@pytest.mark.django_db
@pytest.mark.integration
class TestImportCatalogCommand:
    """Тесты команды импорта каталога из 1С"""

    def test_command_requires_data_dir_argument(self):
        """Проверка что команда требует аргумент --data-dir"""
        with pytest.raises(CommandError, match="--data-dir"):
            call_command("import_catalog_from_1c")

    def test_command_validates_directory_exists(self):
        """Проверка валидации существования директории"""
        with pytest.raises(CommandError, match="Директория не найдена"):
            call_command("import_catalog_from_1c", "--data-dir", "/nonexistent/path")

    def test_command_validates_directory_structure(self, tmp_path):
        """Проверка валидации структуры директории"""
        # Создаем директорию без обязательных поддиректорий
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()

        with pytest.raises(
            CommandError, match="Отсутствует обязательная поддиректория"
        ):
            call_command("import_catalog_from_1c", "--data-dir", str(test_dir))

    def test_dry_run_mode(self, tmp_path):
        """Проверка режима dry-run"""
        # Создаем структуру директорий
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()

        for subdir in ["goods", "offers", "prices", "rests", "priceLists"]:
            (test_dir / subdir).mkdir()

        # Создаем пустые XML файлы
        goods_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Каталог>
  <Товары>
    <Товар>
      <Ид>test-uuid</Ид>
      <Наименование>Тест</Наименование>
    </Товар>
  </Товары>
</Каталог>"""
        (test_dir / "goods" / "goods.xml").write_text(goods_xml, encoding="utf-8")

        # Запускаем в dry-run режиме
        out = StringIO()
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(test_dir),
            "--dry-run",
            stdout=out,
        )

        output = out.getvalue()
        assert "DRY RUN MODE" in output
        assert "Проверка goods.xml" in output

        # Проверяем что сессия не создана
        assert ImportSession.objects.count() == 0

    def test_import_creates_import_session(self, tmp_path):
        """Проверка создания ImportSession"""
        # Подготовка тестовых данных
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()

        for subdir in ["goods", "offers", "prices", "rests", "priceLists"]:
            (test_dir / subdir).mkdir()

        # Минимальные XML файлы
        goods_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Каталог><Товары></Товары></Каталог>"""
        (test_dir / "goods" / "goods.xml").write_text(goods_xml, encoding="utf-8")

        offers_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений><Предложения></Предложения></ПакетПредложений>"""
        (test_dir / "offers" / "offers.xml").write_text(offers_xml, encoding="utf-8")

        # Запускаем импорт
        try:
            call_command("import_catalog_from_1c", "--data-dir", str(test_dir))
        except Exception:
            # Команда может упасть из-за отсутствия данных, но
            # сессия должна создаться
            pass

        # Проверяем что сессия создана
        assert ImportSession.objects.count() >= 1
        session = ImportSession.objects.first()
        assert session is not None
        assert session.import_type == ImportSession.ImportType.CATALOG

    @pytest.mark.slow
    def test_successful_import_with_test_data(self, tmp_path):
        """Проверка успешного импорта тестовых данных"""
        # Подготовка полных тестовых данных
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()

        for subdir in ["goods", "offers", "prices", "rests", "priceLists"]:
            (test_dir / subdir).mkdir()

        # Создаем полноценные XML файлы
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
        (test_dir / "priceLists" / "priceLists.xml").write_text(
            price_lists_xml, encoding="utf-8"
        )

        goods_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Каталог>
  <Товары>
    <Товар>
      <Ид>parent-uuid-001</Ид>
      <Наименование>Тестовый товар</Наименование>
      <Артикул>TEST-001</Артикул>
    </Товар>
  </Товары>
</Каталог>"""
        (test_dir / "goods" / "goods.xml").write_text(goods_xml, encoding="utf-8")

        offers_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
    <Предложение>
      <Ид>parent-uuid-001#sku-uuid-001</Ид>
      <Наименование>Тестовый товар SKU</Наименование>
      <Артикул>TEST-001-SKU</Артикул>
    </Предложение>
  </Предложения>
</ПакетПредложений>"""
        (test_dir / "offers" / "offers.xml").write_text(offers_xml, encoding="utf-8")

        prices_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
    <Предложение>
      <Ид>parent-uuid-001#sku-uuid-001</Ид>
      <Цены>
        <Цена>
          <ИдТипаЦены>retail-uuid</ИдТипаЦены>
          <ЦенаЗаЕдиницу>1000.00</ЦенаЗаЕдиницу>
        </Цена>
      </Цены>
    </Предложение>
  </Предложения>
</ПакетПредложений>"""
        (test_dir / "prices" / "prices.xml").write_text(prices_xml, encoding="utf-8")

        rests_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
    <Предложение>
      <Ид>parent-uuid-001#sku-uuid-001</Ид>
      <Остатки>
        <Остаток>
          <Склад>warehouse-1</Склад>
          <Количество>50</Количество>
        </Остаток>
      </Остатки>
    </Предложение>
  </Предложения>
</ПакетПредложений>"""
        (test_dir / "rests" / "rests.xml").write_text(rests_xml, encoding="utf-8")

        # Запускаем импорт
        out = StringIO()
        call_command("import_catalog_from_1c", "--data-dir", str(test_dir), stdout=out)

        output = out.getvalue()
        assert "ИМПОРТ ЗАВЕРШЕН УСПЕШНО" in output

        # Проверяем результаты
        assert Product.objects.filter(parent_onec_id="parent-uuid-001").exists()
        product = Product.objects.get(parent_onec_id="parent-uuid-001")
        assert product.onec_id == "parent-uuid-001#sku-uuid-001"
        assert product.is_active is True

        # Проверяем статус сессии
        session = ImportSession.objects.latest("started_at")
        assert session.status == ImportSession.ImportStatus.COMPLETED

    def test_import_supports_segmented_files(self, tmp_path):
        """Проверка импорта сегментированных файлов goods_*.xml и др."""

        test_dir = tmp_path / "segmented_data"
        test_dir.mkdir()

        for subdir in ["goods", "offers", "prices", "rests", "priceLists"]:
            (test_dir / subdir).mkdir()

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
        (test_dir / "priceLists" / "priceLists_1.xml").write_text(
            price_lists_xml, encoding="utf-8"
        )

        goods_xml_part1 = """<?xml version="1.0" encoding="UTF-8"?>
<Каталог>
  <Товары>
    <Товар>
      <Ид>parent-uuid-001</Ид>
      <Наименование>Тестовый товар 1</Наименование>
      <Артикул>TEST-001</Артикул>
    </Товар>
  </Товары>
</Каталог>"""
        goods_xml_part2 = """<?xml version="1.0" encoding="UTF-8"?>
<Каталог>
  <Товары>
    <Товар>
      <Ид>parent-uuid-002</Ид>
      <Наименование>Тестовый товар 2</Наименование>
      <Артикул>TEST-002</Артикул>
    </Товар>
  </Товары>
</Каталог>"""
        (test_dir / "goods" / "goods_1_1.xml").write_text(
            goods_xml_part1, encoding="utf-8"
        )
        (test_dir / "goods" / "goods_1_2.xml").write_text(
            goods_xml_part2, encoding="utf-8"
        )

        offers_part1 = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
    <Предложение>
      <Ид>parent-uuid-001#sku-uuid-001</Ид>
      <Наименование>Тестовый товар 1 SKU</Наименование>
      <Артикул>TEST-001-SKU</Артикул>
    </Предложение>
  </Предложения>
</ПакетПредложений>"""
        offers_part2 = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
    <Предложение>
      <Ид>parent-uuid-002#sku-uuid-002</Ид>
      <Наименование>Тестовый товар 2 SKU</Наименование>
      <Артикул>TEST-002-SKU</Артикул>
    </Предложение>
  </Предложения>
</ПакетПредложений>"""
        (test_dir / "offers" / "offers_1.xml").write_text(
            offers_part1, encoding="utf-8"
        )
        (test_dir / "offers" / "offers_2.xml").write_text(
            offers_part2, encoding="utf-8"
        )

        prices_part1 = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
    <Предложение>
      <Ид>parent-uuid-001#sku-uuid-001</Ид>
      <Цены>
        <Цена>
          <ИдТипаЦены>retail-uuid</ИдТипаЦены>
          <ЦенаЗаЕдиницу>1000.00</ЦенаЗаЕдиницу>
        </Цена>
      </Цены>
    </Предложение>
  </Предложения>
</ПакетПредложений>"""
        prices_part2 = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
    <Предложение>
      <Ид>parent-uuid-002#sku-uuid-002</Ид>
      <Цены>
        <Цена>
          <ИдТипаЦены>retail-uuid</ИдТипаЦены>
          <ЦенаЗаЕдиницу>2000.00</ЦенаЗаЕдиницу>
        </Цена>
      </Цены>
    </Предложение>
  </Предложения>
</ПакетПредложений>"""
        (test_dir / "prices" / "prices_1.xml").write_text(
            prices_part1, encoding="utf-8"
        )
        (test_dir / "prices" / "prices_2.xml").write_text(
            prices_part2, encoding="utf-8"
        )

        rests_part1 = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
    <Предложение>
      <Ид>parent-uuid-001#sku-uuid-001</Ид>
      <Остатки>
        <Остаток>
          <Склад>warehouse-1</Склад>
          <Количество>10</Количество>
        </Остаток>
      </Остатки>
    </Предложение>
  </Предложения>
</ПакетПредложений>"""
        rests_part2 = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
    <Предложение>
      <Ид>parent-uuid-002#sku-uuid-002</Ид>
      <Остатки>
        <Остаток>
          <Склад>warehouse-2</Склад>
          <Количество>5</Количество>
        </Остаток>
      </Остатки>
    </Предложение>
  </Предложения>
</ПакетПредложений>"""
        (test_dir / "rests" / "rests_1.xml").write_text(rests_part1, encoding="utf-8")
        (test_dir / "rests" / "rests_2.xml").write_text(rests_part2, encoding="utf-8")

        call_command("import_catalog_from_1c", "--data-dir", str(test_dir))

        assert (
            Product.objects.filter(
                parent_onec_id__in=["parent-uuid-001", "parent-uuid-002"]
            ).count()
            == 2
        )

        prod1 = Product.objects.get(parent_onec_id="parent-uuid-001")
        prod2 = Product.objects.get(parent_onec_id="parent-uuid-002")

        assert prod1.retail_price == Decimal("1000.00")
        assert prod2.retail_price == Decimal("2000.00")
        assert prod1.stock_quantity == 10
        assert prod2.stock_quantity == 5

        session = ImportSession.objects.latest("started_at")
        assert session.status == ImportSession.ImportStatus.COMPLETED
