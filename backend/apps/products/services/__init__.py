"""
Services для работы с импортом данных из 1С
"""
from .parser import XMLDataParser
from .processor import ProductDataProcessor

__all__ = ["XMLDataParser", "ProductDataProcessor"]
