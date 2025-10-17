"""
XMLDataParser - парсер для XML файлов из 1С (CommerceML 3.1)
"""
import os
from decimal import Decimal
from typing import Any
from xml.etree.ElementTree import ElementTree

import defusedxml.ElementTree as ET
from django.conf import settings


class XMLDataParser:
    """
    Парсер для обработки XML файлов из 1С в формате CommerceML 3.1

    Методы:
    - parse_goods_xml() - парсинг goods.xml (базовые товары)
    - parse_offers_xml() - парсинг offers.xml (SKU/предложения)
    - parse_prices_xml() - парсинг prices.xml (цены)
    - parse_rests_xml() - парсинг rests.xml (остатки)
    - parse_price_lists_xml() - парсинг priceLists.xml (типы цен)
    """

    MAX_FILE_SIZE = getattr(settings, "IMPORT_MAX_FILE_SIZE", 100) * 1024 * 1024  # MB to bytes

    def __init__(self):
        pass

    def _validate_file(self, file_path: str) -> None:
        """Валидация файла перед парсингом"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File size {file_size} bytes exceeds limit {self.MAX_FILE_SIZE} bytes"
            )

    def _safe_parse_xml(self, file_path: str) -> ElementTree:
        """Безопасный парсинг XML с защитой от XXE и XML Bomb"""
        self._validate_file(file_path)

        try:
            tree = ET.parse(file_path)
            return tree
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML structure in {file_path}: {e}")

    def parse_goods_xml(self, file_path: str) -> list[dict[str, Any]]:
        """Парсинг goods.xml - базовые товары"""
        tree = self._safe_parse_xml(file_path)
        root = tree.getroot()

        goods_list = []
        # CommerceML структура: <Каталог><Товары><Товар>
        for товар in root.findall(".//Товар"):
            goods_data = {
                "id": товар.findtext("Ид", "").strip(),
                "name": товар.findtext("Наименование", "").strip(),
                "description": товар.findtext("Описание", "").strip(),
                "article": товар.findtext("Артикул", "").strip(),
            }

            # Категория
            группы = товар.find("Группы")
            if группы is not None:
                category_id = группы.findtext("Ид", "").strip()
                goods_data["category_id"] = category_id

            # Изображения
            картинки = товар.findall("Картинка")
            if картинки:
                goods_data["images"] = [
                    к.text.strip() for к in картинки if к.text
                ]

            if goods_data["id"]:  # Только если есть ID
                goods_list.append(goods_data)

        return goods_list

    def parse_offers_xml(self, file_path: str) -> list[dict[str, Any]]:
        """Парсинг offers.xml - торговые предложения (SKU)"""
        tree = self._safe_parse_xml(file_path)
        root = tree.getroot()

        offers_list = []
        # CommerceML структура: <ПакетПредложений><Предложения><Предложение>
        for предложение in root.findall(".//Предложение"):
            offer_data = {
                "id": предложение.findtext("Ид", "").strip(),
                "name": предложение.findtext("Наименование", "").strip(),
                "article": предложение.findtext("Артикул", "").strip(),
            }

            # Характеристики (размер, цвет и т.д.)
            характеристики = предложение.find("ХарактеристикиТовара")
            if характеристики is not None:
                char_list = []
                for харак in характеристики.findall("ХарактеристикаТовара"):
                    char_name = харак.findtext("Наименование", "").strip()
                    char_value = харак.findtext("Значение", "").strip()
                    if char_name and char_value:
                        char_list.append({"name": char_name, "value": char_value})
                if char_list:
                    offer_data["characteristics"] = char_list

            if offer_data["id"]:  # Только если есть ID
                offers_list.append(offer_data)

        return offers_list

    def parse_prices_xml(self, file_path: str) -> list[dict[str, Any]]:
        """Парсинг prices.xml - цены"""
        tree = self._safe_parse_xml(file_path)
        root = tree.getroot()

        prices_list = []
        # CommerceML структура: <ПакетПредложений><Предложения><Предложение>
        for предложение in root.findall(".//Предложение"):
            offer_id = предложение.findtext("Ид", "").strip()
            if not offer_id:
                continue

            prices_data = {"id": offer_id, "prices": []}

            # Цены
            цены = предложение.find("Цены")
            if цены is not None:
                for цена in цены.findall("Цена"):
                    price_type_id = цена.findtext("ИдТипаЦены", "").strip()
                    price_value = цена.findtext("ЦенаЗаЕдиницу", "0").strip()

                    try:
                        price_decimal = Decimal(price_value)
                        prices_data["prices"].append({
                            "price_type_id": price_type_id,
                            "value": price_decimal,
                        })
                    except (ValueError, TypeError):
                        # Пропускаем некорректные цены
                        continue

            if prices_data["prices"]:  # Только если есть цены
                prices_list.append(prices_data)

        return prices_list

    def parse_rests_xml(self, file_path: str) -> list[dict[str, Any]]:
        """Парсинг rests.xml - остатки"""
        tree = self._safe_parse_xml(file_path)
        root = tree.getroot()

        rests_list = []
        # CommerceML структура: <ПакетПредложений><Предложения><Предложение>
        for предложение in root.findall(".//Предложение"):
            offer_id = предложение.findtext("Ид", "").strip()
            if not offer_id:
                continue

            остатки = предложение.find("Остатки")
            if остатки is not None:
                for остаток in остатки.findall("Остаток"):
                    warehouse_id = остаток.findtext("Склад", "").strip()
                    quantity = остаток.findtext("Количество", "0").strip()

                    try:
                        qty_int = int(float(quantity))
                        rests_list.append({
                            "id": offer_id,
                            "warehouse_id": warehouse_id,
                            "quantity": qty_int,
                        })
                    except (ValueError, TypeError):
                        # Пропускаем некорректные остатки
                        continue

        return rests_list

    def parse_price_lists_xml(self, file_path: str) -> list[dict[str, Any]]:
        """Парсинг priceLists.xml - типы цен"""
        tree = self._safe_parse_xml(file_path)
        root = tree.getroot()

        price_types = []
        # CommerceML структура: <ПакетПредложений><ТипыЦен><ТипЦены>
        for тип_цены in root.findall(".//ТипЦены"):
            price_type_data = {
                "onec_id": тип_цены.findtext("Ид", "").strip(),
                "onec_name": тип_цены.findtext("Наименование", "").strip(),
                "currency": тип_цены.findtext("Валюта", "RUB").strip(),
            }

            # Определяем маппинг на поле Product
            product_field = self._map_price_type_to_field(price_type_data["onec_name"])
            price_type_data["product_field"] = product_field

            if price_type_data["onec_id"] and price_type_data["onec_name"]:
                price_types.append(price_type_data)

        return price_types

    def _map_price_type_to_field(self, onec_name: str) -> str:
        """Маппинг названия типа цены из 1С на поле Product"""
        name_lower = onec_name.lower()

        if "опт 1" in name_lower or "опт1" in name_lower:
            return "opt1_price"
        elif "опт 2" in name_lower or "опт2" in name_lower:
            return "opt2_price"
        elif "опт 3" in name_lower or "опт3" in name_lower:
            return "opt3_price"
        elif "тренер" in name_lower:
            return "trainer_price"
        elif "ррц" in name_lower and "рекомендован" in name_lower:
            return "recommended_retail_price"
        elif "ррц" in name_lower:
            return "retail_price"
        elif "мрц" in name_lower:
            return "max_suggested_retail_price"
        else:
            # По умолчанию - розничная цена
            return "retail_price"
