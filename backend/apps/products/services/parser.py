"""
XMLDataParser - парсер для XML файлов из 1С (CommerceML 3.1)
"""
import os
from decimal import Decimal
from typing import Any, Iterator, TypedDict, cast
from xml.etree.ElementTree import Element, ElementTree

import defusedxml.ElementTree as ET
from django.conf import settings


class GoodsData(TypedDict, total=False):
    id: str
    name: str
    description: str
    article: str
    category_id: str
    category_name: str
    images: list[str]


class OfferCharacteristic(TypedDict):
    name: str
    value: str


class OfferData(TypedDict, total=False):
    id: str
    name: str
    article: str
    characteristics: list[OfferCharacteristic]


class PriceItem(TypedDict):
    price_type_id: str
    value: Decimal


class PriceData(TypedDict):
    id: str
    prices: list[PriceItem]


class RestData(TypedDict):
    id: str
    warehouse_id: str
    quantity: int


class PriceTypeData(TypedDict):
    onec_id: str
    onec_name: str
    currency: str
    product_field: str


class CategoryData(TypedDict, total=False):
    """Данные категории из groups.xml"""

    id: str
    name: str
    parent_id: str
    description: str


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

    MAX_FILE_SIZE = (
        getattr(settings, "IMPORT_MAX_FILE_SIZE", 100) * 1024 * 1024
    )  # MB to bytes

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
            tree: ElementTree = cast(ElementTree, ET.parse(file_path))
            root = cast(Element, tree.getroot())
            self._strip_namespace(root)
            return tree
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML structure in {file_path}: {e}")

    def _strip_namespace(self, root: Element) -> None:
        """Удаляет namespace из тегов для упрощения XPath-поиска."""

        for elem in root.iter():
            local_tag = self._get_local_tag(elem.tag)
            if local_tag:
                elem.tag = local_tag

    def _get_local_tag(self, tag: Any) -> str:
        """Возвращает имя тега без namespace."""

        if not isinstance(tag, str):
            return ""
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    def _iter_elements(self, root: Element, tag: str) -> Iterator[Element]:
        """Итератор по элементам с указанным именем тега (без namespace)."""

        for elem in root.iter():
            if self._get_local_tag(elem.tag) == tag:
                yield elem

    def _find_child(self, element: Element, tag: str) -> Element | None:
        """Возвращает первого потомка с нужным именем тега."""

        for child in list(element):
            if self._get_local_tag(child.tag) == tag:
                return child
        return None

    def _find_children(self, element: Element, tag: str) -> list[Element]:
        """Возвращает всех прямых потомков с нужным именем тега."""

        return [
            child for child in list(element) if self._get_local_tag(child.tag) == tag
        ]

    def _find_text(self, element: Element, tag: str, default: str = "") -> str:
        """Возвращает текст первого потомка с указанным именем тега."""

        child = self._find_child(element, tag)
        if child is not None and child.text:
            return child.text.strip()
        return default

    def parse_goods_xml(self, file_path: str) -> list[GoodsData]:
        """Парсинг goods.xml - базовые товары"""
        tree = self._safe_parse_xml(file_path)
        root = cast(Element, tree.getroot())

        goods_list: list[GoodsData] = []
        # CommerceML структура: <Каталог><Товары><Товар>
        for product_element in root.findall(".//Товар"):
            goods_data: GoodsData = {
                "id": self._find_text(product_element, "Ид"),
                "name": self._find_text(product_element, "Наименование"),
                "description": self._find_text(product_element, "Описание"),
                "article": self._find_text(product_element, "Артикул"),
            }

            groups_element = self._find_child(product_element, "Группы")
            if groups_element is not None:
                goods_data["category_id"] = self._find_text(groups_element, "Ид")
                category_name = self._find_text(groups_element, "Наименование")
                if category_name:
                    goods_data["category_name"] = category_name

            image_elements = self._find_children(product_element, "Картинка")
            if image_elements:
                goods_data["images"] = [
                    image.text.strip() for image in image_elements if image.text
                ]

            if goods_data.get("id"):  # Только если есть ID
                goods_list.append(goods_data)

        return goods_list

    def parse_offers_xml(self, file_path: str) -> list[OfferData]:
        """Парсинг offers.xml - торговые предложения (SKU)"""
        tree = self._safe_parse_xml(file_path)
        root = cast(Element, tree.getroot())

        offers_list: list[OfferData] = []
        # CommerceML структура: <ПакетПредложений><Предложения><Предложение>
        for offer_element in root.findall(".//Предложение"):
            offer_data: OfferData = {
                "id": self._find_text(offer_element, "Ид"),
                "name": self._find_text(offer_element, "Наименование"),
                "article": self._find_text(offer_element, "Артикул"),
            }

            characteristics_element = self._find_child(
                offer_element, "ХарактеристикиТовара"
            )
            if characteristics_element is not None:
                char_list: list[OfferCharacteristic] = []
                for characteristics_item in self._find_children(
                    characteristics_element, "ХарактеристикаТовара"
                ):
                    char_name = self._find_text(characteristics_item, "Наименование")
                    char_value = self._find_text(characteristics_item, "Значение")
                    if char_name and char_value:
                        char_list.append({"name": char_name, "value": char_value})
                if char_list:
                    offer_data["characteristics"] = char_list

            if offer_data.get("id"):  # Только если есть ID
                offers_list.append(offer_data)

        return offers_list

    def parse_prices_xml(self, file_path: str) -> list[PriceData]:
        """Парсинг prices.xml - цены"""
        tree = self._safe_parse_xml(file_path)
        root = cast(Element, tree.getroot())

        prices_list: list[PriceData] = []
        # CommerceML структура: <ПакетПредложений><Предложения><Предложение>
        for price_offer_element in root.findall(".//Предложение"):
            offer_id = self._find_text(price_offer_element, "Ид")
            if not offer_id:
                continue

            prices_data: PriceData = {"id": offer_id, "prices": []}

            prices_element = self._find_child(price_offer_element, "Цены")
            if prices_element is not None:
                for price_element in self._find_children(prices_element, "Цена"):
                    price_type_id = self._find_text(price_element, "ИдТипаЦены")
                    price_value = self._find_text(price_element, "ЦенаЗаЕдиницу", "0")

                    if not price_type_id:
                        continue

                    try:
                        price_decimal = Decimal(price_value)
                        price_item: PriceItem = {
                            "price_type_id": price_type_id,
                            "value": price_decimal,
                        }
                        prices_data["prices"].append(price_item)
                    except (ValueError, TypeError):
                        continue

            if prices_data["prices"]:  # Только если есть цены
                prices_list.append(prices_data)

        return prices_list

    def parse_rests_xml(self, file_path: str) -> list[RestData]:
        """Парсинг rests.xml - остатки"""
        tree = self._safe_parse_xml(file_path)
        root = cast(Element, tree.getroot())

        rests_list: list[RestData] = []
        # CommerceML структура: <ПакетПредложений><Предложения><Предложение>
        for rest_offer_element in root.findall(".//Предложение"):
            offer_id = self._find_text(rest_offer_element, "Ид")
            if not offer_id:
                continue

            rests_element = self._find_child(rest_offer_element, "Остатки")
            if rests_element is None:
                continue

            for rest_element in self._find_children(rests_element, "Остаток"):
                warehouse_element = self._find_child(rest_element, "Склад")
                if warehouse_element is not None:
                    warehouse_id = self._find_text(warehouse_element, "Ид")
                    if not warehouse_id:
                        warehouse_id = (warehouse_element.text or "").strip()

                    quantity_value = self._find_text(warehouse_element, "Количество")
                    if not quantity_value:
                        quantity_value = self._find_text(
                            rest_element, "Количество", "0"
                        )
                else:
                    warehouse_id = self._find_text(rest_element, "Склад")
                    quantity_value = self._find_text(rest_element, "Количество", "0")

                try:
                    qty_int = int(float(quantity_value))
                except (ValueError, TypeError):
                    continue

                rest_item: RestData = {
                    "id": offer_id,
                    "warehouse_id": warehouse_id,
                    "quantity": qty_int,
                }
                rests_list.append(rest_item)

        return rests_list

    def parse_price_lists_xml(self, file_path: str) -> list[PriceTypeData]:
        """Парсинг priceLists.xml - типы цен"""
        tree = self._safe_parse_xml(file_path)
        root = cast(Element, tree.getroot())

        price_types: list[PriceTypeData] = []
        # CommerceML структура: <ПакетПредложений><ТипыЦен><ТипЦены>
        for price_type_element in root.findall(".//ТипЦены"):
            onec_id = self._find_text(price_type_element, "Ид")
            onec_name = self._find_text(price_type_element, "Наименование")
            currency = self._find_text(price_type_element, "Валюта", "RUB")
            product_field = self._map_price_type_to_field(onec_name)

            price_type_data: PriceTypeData = {
                "onec_id": onec_id,
                "onec_name": onec_name,
                "currency": currency,
                "product_field": product_field,
            }

            if price_type_data["onec_id"] and price_type_data["onec_name"]:
                price_types.append(price_type_data)

        return price_types

    def parse_groups_xml(self, file_path: str) -> list[CategoryData]:
        """
        Парсинг groups.xml - иерархия категорий (Story 3.1.2)

        Поддерживает многоуровневую вложенность категорий.
        Структура: <Классификатор><Группы><Группа>
        """
        tree = self._safe_parse_xml(file_path)
        root = cast(Element, tree.getroot())

        categories_list: list[CategoryData] = []

        # Рекурсивная функция для обхода иерархии
        def parse_group(group_element: Element, parent_id: str = "") -> None:
            category_id = self._find_text(group_element, "Ид")
            category_name = self._find_text(group_element, "Наименование")

            if not category_id or not category_name:
                return

            category_data: CategoryData = {
                "id": category_id,
                "name": category_name,
                "description": self._find_text(group_element, "Описание"),
            }

            if parent_id:
                category_data["parent_id"] = parent_id

            categories_list.append(category_data)

            # Рекурсивно обрабатываем вложенные группы
            child_groups_element = self._find_child(group_element, "Группы")
            if child_groups_element is not None:
                for child_group in self._find_children(child_groups_element, "Группа"):
                    parse_group(child_group, parent_id=category_id)

        # Ищем корневой элемент Группы в Классификаторе или Каталоге
        groups_container = (
            root.find(".//Классификатор/Группы")
            or root.find(".//Каталог/Группы")
            or root.find(".//Группы")
        )

        if groups_container is not None:
            for group_element in self._find_children(groups_container, "Группа"):
                parse_group(group_element)

        return categories_list

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
