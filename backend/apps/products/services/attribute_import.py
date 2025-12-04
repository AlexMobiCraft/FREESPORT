"""
AttributeImportService - сервис для импорта атрибутов из 1С

Парсит XML файлы propertiesGoods/*.xml и propertiesOffers/*.xml,
создает/обновляет записи Attribute и AttributeValue.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

import defusedxml.ElementTree as ET
from django.conf import settings
from django.db import transaction

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from apps.products.models import Attribute, AttributeValue

logger = logging.getLogger(__name__)


class AttributeImportService:
    """
    Сервис импорта атрибутов из XML файлов 1С (CommerceML 3.1)

    Обрабатывает файлы propertiesGoods/*.xml и propertiesOffers/*.xml,
    извлекает определения свойств (Attribute) и их значения (AttributeValue),
    сохраняет в БД с дедупликацией по onec_id.
    """

    NAMESPACE = {"ns": "urn:1C.ru:commerceml_3"}
    MAX_FILE_SIZE = (
        getattr(settings, "IMPORT_MAX_FILE_SIZE", 100) * 1024 * 1024
    )  # MB to bytes

    def __init__(self) -> None:
        """Инициализация сервиса"""
        from apps.products.models import Attribute, AttributeValue

        self.attribute_model: type[Attribute] = Attribute
        self.attribute_value_model: type[AttributeValue] = AttributeValue
        self.stats = {
            "attributes_created": 0,
            "attributes_updated": 0,
            "values_created": 0,
            "values_updated": 0,
            "errors": 0,
        }

    def import_from_directory(self, directory_path: str) -> dict[str, int]:
        """
        Импортировать атрибуты из всех XML файлов в директории

        Args:
            directory_path: Путь к директории с XML файлами

        Returns:
            Статистика импорта (created, updated, errors)
        """
        if not os.path.exists(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        if not os.path.isdir(directory_path):
            logger.error(f"Path is not a directory: {directory_path}")
            raise ValueError(f"Path is not a directory: {directory_path}")

        xml_files = [f for f in os.listdir(directory_path) if f.endswith(".xml")]

        if not xml_files:
            logger.warning(f"No XML files found in {directory_path}")
            return self.stats

        logger.info(f"Found {len(xml_files)} XML files in {directory_path}")

        for filename in xml_files:
            file_path = os.path.join(directory_path, filename)
            try:
                self.import_from_file(file_path)
            except Exception as e:
                logger.error(f"Error processing file {filename}: {e}")
                self.stats["errors"] += 1

        logger.info(f"Import completed. Stats: {self.stats}")
        return self.stats

    def import_from_file(self, file_path: str) -> None:
        """
        Импортировать атрибуты из одного XML файла

        Args:
            file_path: Путь к XML файлу
        """
        self._validate_file(file_path)

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Парсинг свойств из <Классификатор><Свойства>
            properties = self._parse_properties(root)

            # Сохранение в БД с транзакцией
            self._save_properties(properties)

            logger.info(f"Successfully processed file: {file_path}")

        except ET.ParseError as e:
            logger.error(f"XML parse error in {file_path}: {e}")
            self.stats["errors"] += 1
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing {file_path}: {e}")
            self.stats["errors"] += 1
            raise

    def _validate_file(self, file_path: str) -> None:
        """Валидация файла перед парсингом"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File {file_path} is too large: "
                f"{file_size / (1024 * 1024):.2f} MB "
                f"(max: {self.MAX_FILE_SIZE / (1024 * 1024):.2f} MB)"
            )

        if file_size == 0:
            raise ValueError(f"File {file_path} is empty")

    def _parse_properties(self, root: Element) -> list[dict[str, Any]]:
        """
        Парсинг свойств из XML

        Args:
            root: Корневой элемент XML дерева

        Returns:
            Список словарей с данными свойств
        """
        properties = []

        # Поиск всех элементов <Свойство> внутри <Классификатор><Свойства>
        classifier = root.find(".//ns:Классификатор", self.NAMESPACE)
        if classifier is None:
            logger.warning("No <Классификатор> found in XML")
            return properties

        properties_section = classifier.find("ns:Свойства", self.NAMESPACE)
        if properties_section is None:
            logger.warning("No <Свойства> section found in XML")
            return properties

        for prop_elem in properties_section.findall("ns:Свойство", self.NAMESPACE):
            try:
                property_data = self._parse_property_element(prop_elem)
                if property_data:
                    properties.append(property_data)
            except Exception as e:
                logger.error(f"Error parsing property element: {e}")
                continue

        logger.info(f"Parsed {len(properties)} properties from XML")
        return properties

    def _parse_property_element(self, prop_elem: Element) -> dict[str, Any] | None:
        """
        Парсинг одного элемента <Свойство>

        Args:
            prop_elem: XML элемент <Свойство>

        Returns:
            Словарь с данными свойства или None если парсинг не удался
        """
        # Обязательные поля
        onec_id_elem = prop_elem.find("ns:Ид", self.NAMESPACE)
        name_elem = prop_elem.find("ns:Наименование", self.NAMESPACE)
        type_elem = prop_elem.find("ns:ТипЗначений", self.NAMESPACE)

        if onec_id_elem is None or name_elem is None:
            logger.warning("Property missing required fields (Ид or Наименование)")
            return None

        onec_id = onec_id_elem.text
        name = name_elem.text
        attr_type = type_elem.text if type_elem is not None else ""

        if not onec_id or not name:
            logger.warning("Property has empty Ид or Наименование")
            return None

        # Парсинг значений (если есть <ВариантыЗначений>)
        values = []
        values_section = prop_elem.find("ns:ВариантыЗначений", self.NAMESPACE)
        if values_section is not None:
            for value_elem in values_section.findall("ns:Справочник", self.NAMESPACE):
                value_id_elem = value_elem.find("ns:ИдЗначения", self.NAMESPACE)
                value_text_elem = value_elem.find("ns:Значение", self.NAMESPACE)

                if value_id_elem is not None and value_text_elem is not None:
                    value_id = value_id_elem.text
                    value_text = value_text_elem.text

                    if value_id and value_text:
                        values.append(
                            {"onec_id": value_id, "value": value_text.strip()}
                        )

        return {
            "onec_id": onec_id,
            "name": name.strip(),
            "type": attr_type,
            "values": values,
        }

    @transaction.atomic
    def _save_properties(self, properties: list[dict[str, Any]]) -> None:
        """
        Сохранение свойств в БД с дедупликацией

        Args:
            properties: Список словарей с данными свойств
        """
        for prop_data in properties:
            try:
                # Создание/обновление атрибута
                attribute, created = self.attribute_model.objects.update_or_create(
                    onec_id=prop_data["onec_id"],
                    defaults={"name": prop_data["name"], "type": prop_data["type"]},
                )

                if created:
                    self.stats["attributes_created"] += 1
                    logger.debug(
                        f"Created attribute: {attribute.name} ({attribute.onec_id})"
                    )
                else:
                    self.stats["attributes_updated"] += 1
                    logger.debug(
                        f"Updated attribute: {attribute.name} ({attribute.onec_id})"
                    )

                # Создание/обновление значений атрибута
                for value_data in prop_data["values"]:
                    (
                        value_obj,
                        value_created,
                    ) = self.attribute_value_model.objects.update_or_create(
                        onec_id=value_data["onec_id"],
                        defaults={
                            "attribute": attribute,
                            "value": value_data["value"],
                        },
                    )

                    if value_created:
                        self.stats["values_created"] += 1
                        logger.debug(
                            f"Created value: {value_obj.value} for {attribute.name}"
                        )
                    else:
                        self.stats["values_updated"] += 1
                        logger.debug(
                            f"Updated value: {value_obj.value} for {attribute.name}"
                        )

            except Exception as e:
                logger.error(f"Error saving property {prop_data.get('name')}: {e}")
                self.stats["errors"] += 1
                raise

    def get_stats(self) -> dict[str, int]:
        """Получить статистику импорта"""
        return self.stats.copy()

    def reset_stats(self) -> None:
        """Сбросить статистику"""
        self.stats = {
            "attributes_created": 0,
            "attributes_updated": 0,
            "values_created": 0,
            "values_updated": 0,
            "errors": 0,
        }
