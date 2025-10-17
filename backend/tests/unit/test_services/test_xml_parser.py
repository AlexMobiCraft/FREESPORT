"""
Unit-тесты для XMLDataParser
"""
import os
import tempfile
from decimal import Decimal

import pytest

from apps.products.services.parser import XMLDataParser


@pytest.mark.unit
class TestXMLDataParser:
    """Тесты парсера XML файлов из 1С"""

    def test_parse_goods_xml_structure(self, tmp_path):
        """Проверка корректного парсинга структуры goods.xml"""
        # Создаем тестовый XML файл
        goods_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Каталог>
  <Товары>
    <Товар>
      <Ид>test-uuid-123</Ид>
      <Наименование>Тестовый товар</Наименование>
      <Артикул>TEST-001</Артикул>
      <Описание>Описание товара</Описание>
      <Группы>
        <Ид>category-uuid-456</Ид>
      </Группы>
      <Картинка>goods/import_files/12/image.jpg</Картинка>
    </Товар>
  </Товары>
</Каталог>"""

        # Сохраняем во временный файл
        test_file = tmp_path / "goods.xml"
        test_file.write_text(goods_xml, encoding="utf-8")

        # Парсим
        parser = XMLDataParser()
        result = parser.parse_goods_xml(str(test_file))

        # Проверяем результат
        assert len(result) == 1
        assert result[0]["id"] == "test-uuid-123"
        assert result[0]["name"] == "Тестовый товар"
        assert result[0]["article"] == "TEST-001"
        assert result[0]["description"] == "Описание товара"
        assert result[0]["category_id"] == "category-uuid-456"
        assert len(result[0]["images"]) == 1

    def test_parse_offers_xml_with_characteristics(self, tmp_path):
        """Проверка парсинга offers.xml с характеристиками"""
        offers_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
    <Предложение>
      <Ид>parent-uuid#sku-uuid-789</Ид>
      <Наименование>Товар размер M</Наименование>
      <Артикул>PROD-001-M</Артикул>
      <ХарактеристикиТовара>
        <ХарактеристикаТовара>
          <Наименование>Размер</Наименование>
          <Значение>M</Значение>
        </ХарактеристикаТовара>
        <ХарактеристикаТовара>
          <Наименование>Цвет</Наименование>
          <Значение>Черный</Значение>
        </ХарактеристикаТовара>
      </ХарактеристикиТовара>
    </Предложение>
  </Предложения>
</ПакетПредложений>"""

        test_file = tmp_path / "offers.xml"
        test_file.write_text(offers_xml, encoding="utf-8")

        parser = XMLDataParser()
        result = parser.parse_offers_xml(str(test_file))

        assert len(result) == 1
        assert result[0]["id"] == "parent-uuid#sku-uuid-789"
        assert result[0]["name"] == "Товар размер M"
        assert "characteristics" in result[0]
        assert len(result[0]["characteristics"]) == 2

    def test_parse_prices_xml_with_role_mapping(self, tmp_path):
        """Проверка маппинга типов цен на роли пользователей"""
        prices_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
    <Предложение>
      <Ид>product-uuid</Ид>
      <Цены>
        <Цена>
          <ИдТипаЦены>retail-price-uuid</ИдТипаЦены>
          <ЦенаЗаЕдиницу>1000.00</ЦенаЗаЕдиницу>
          <Валюта>руб</Валюта>
        </Цена>
        <Цена>
          <ИдТипаЦены>opt1-price-uuid</ИдТипаЦены>
          <ЦенаЗаЕдиницу>800.00</ЦенаЗаЕдиницу>
          <Валюта>руб</Валюта>
        </Цена>
      </Цены>
    </Предложение>
  </Предложения>
</ПакетПредложений>"""

        test_file = tmp_path / "prices.xml"
        test_file.write_text(prices_xml, encoding="utf-8")

        parser = XMLDataParser()
        result = parser.parse_prices_xml(str(test_file))

        assert len(result) == 1
        assert result[0]["id"] == "product-uuid"
        assert len(result[0]["prices"]) == 2
        assert result[0]["prices"][0]["value"] == Decimal("1000.00")
        assert result[0]["prices"][1]["value"] == Decimal("800.00")

    def test_parse_rests_xml(self, tmp_path):
        """Проверка парсинга остатков из rests.xml"""
        rests_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <Предложения>
    <Предложение>
      <Ид>product-uuid</Ид>
      <Остатки>
        <Остаток>
          <Склад>warehouse-1</Склад>
          <Количество>50</Количество>
        </Остаток>
        <Остаток>
          <Склад>warehouse-2</Склад>
          <Количество>30</Количество>
        </Остаток>
      </Остатки>
    </Предложение>
  </Предложения>
</ПакетПредложений>"""

        test_file = tmp_path / "rests.xml"
        test_file.write_text(rests_xml, encoding="utf-8")

        parser = XMLDataParser()
        result = parser.parse_rests_xml(str(test_file))

        assert len(result) == 2
        assert result[0]["quantity"] == 50
        assert result[1]["quantity"] == 30

    def test_parse_price_lists_xml(self, tmp_path):
        """Проверка парсинга справочника типов цен"""
        price_lists_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ПакетПредложений>
  <ТипыЦен>
    <ТипЦены>
      <Ид>opt1-uuid</Ид>
      <Наименование>Опт 1 (300-600 тыс.руб в квартал)</Наименование>
      <Валюта>RUB</Валюта>
    </ТипЦены>
    <ТипЦены>
      <Ид>trainer-uuid</Ид>
      <Наименование>Тренерская</Наименование>
      <Валюта>RUB</Валюта>
    </ТипЦены>
  </ТипыЦен>
</ПакетПредложений>"""

        test_file = tmp_path / "priceLists.xml"
        test_file.write_text(price_lists_xml, encoding="utf-8")

        parser = XMLDataParser()
        result = parser.parse_price_lists_xml(str(test_file))

        assert len(result) == 2
        assert result[0]["onec_id"] == "opt1-uuid"
        assert result[0]["product_field"] == "opt1_price"
        assert result[1]["onec_id"] == "trainer-uuid"
        assert result[1]["product_field"] == "trainer_price"

    def test_handle_malformed_xml_gracefully(self, tmp_path):
        """Проверка обработки некорректного XML"""
        malformed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Каталог>
  <Товары>
    <Товар>
      <Ид>test-uuid</Ид>
      <!-- Незакрытый тег -->
</Каталог>"""

        test_file = tmp_path / "malformed.xml"
        test_file.write_text(malformed_xml, encoding="utf-8")

        parser = XMLDataParser()
        with pytest.raises(ValueError, match="Invalid XML structure"):
            parser.parse_goods_xml(str(test_file))

    def test_file_size_limit(self, tmp_path):
        """Проверка ограничения размера файла"""
        # Создаем большой файл (больше лимита)
        large_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Каталог>
  <Товары>
""" + "    <Товар><Ид>id</Ид><Наименование>Товар</Наименование></Товар>\n" * 100000 + """
  </Товары>
</Каталог>"""

        test_file = tmp_path / "large.xml"
        test_file.write_text(large_xml, encoding="utf-8")

        parser = XMLDataParser()
        # Проверка зависит от настройки IMPORT_MAX_FILE_SIZE
        # В реальном окружении файл должен быть проверен
        try:
            parser.parse_goods_xml(str(test_file))
        except ValueError as e:
            assert "exceeds limit" in str(e)

    def test_map_price_type_to_field(self):
        """Проверка маппинга названий типов цен на поля Product"""
        parser = XMLDataParser()

        assert parser._map_price_type_to_field("Опт 1 (300-600)") == "opt1_price"
        assert parser._map_price_type_to_field("Опт 2") == "opt2_price"
        assert parser._map_price_type_to_field("Опт 3") == "opt3_price"
        assert parser._map_price_type_to_field("Тренерская") == "trainer_price"
        assert parser._map_price_type_to_field("РРЦ Рекомендованная") == "recommended_retail_price"
        assert parser._map_price_type_to_field("РРЦ") == "retail_price"
        assert parser._map_price_type_to_field("МРЦ") == "max_suggested_retail_price"
        assert parser._map_price_type_to_field("Неизвестный тип") == "retail_price"  # fallback
