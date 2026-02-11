import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter

def analyze_file(filepath):
    print(f"--- Анализ файла: {filepath} ---")
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Ошибка парсинга XML: {e}")
        return

    # 1. Версия схемы
    version = root.get("ВерсияСхемы", "Не указана")
    creation_date = root.get("ДатаФормирования", "Не указана")
    print(f"Версия схемы: {version}")
    print(f"Дата формирования: {creation_date}")

    # 2. Структура (Контейнер)
    container = root.find("Контейнер")
    if container is not None:
        print("Тег <Контейнер>: Присутствует")
        docs = container.findall("Документ")
    else:
        print("Тег <Контейнер>: Отсутствует (плоский список?)")
        docs = root.findall("Документ")
    
    print(f"Найдено документов: {len(docs)}")

    if not docs:
        print("Документы не найдены.")
        return

    # 3. Анализ первого документа
    doc = docs[0]
    print("\nСтруктура первого документа:")
    print(f"Ид: {doc.findtext('Ид')}")
    print(f"Номер: {doc.findtext('Номер')}")
    print(f"Дата: {doc.findtext('Дата')}")
    print(f"ХозОперация: {doc.findtext('ХозОперация')}")
    print(f"Роль: {doc.findtext('Роль')}")
    print(f"Валюта: {doc.findtext('Валюта')}")
    print(f"Сумма: {doc.findtext('Сумма')}")

    # 4. Реквизиты
    requisites = doc.find("ЗначенияРеквизитов")
    if requisites is not None:
        print("\nЗначения реквизитов:")
        for req in requisites.findall("ЗначениеРеквизита"):
            name = req.findtext("Наименование")
            value = req.findtext("Значение")
            print(f"  - {name}: {value}")
    else:
        print("\nЗначения реквизитов: Не найдено")

    # 5. Контрагенты
    agents = doc.find("Контрагенты")
    if agents is not None:
        print("\nКонтрагенты:")
        for agent in agents.findall("Контрагент"):
            name = agent.findtext("Наименование")
            role = agent.findtext("Роль")
            print(f"  - {role}: {name}")

def main():
    if len(sys.argv) < 2:
        target_dir = "docs/integrations/1c/samples"
    else:
        target_dir = sys.argv[1]

    if not os.path.exists(target_dir):
        print(f"Директория {target_dir} не найдена.")
        return

    files = [f for f in os.listdir(target_dir) if f.endswith(".xml")]
    if not files:
        print(f"XML файлы не найдены в {target_dir}")
        return

    for f in files:
        analyze_file(os.path.join(target_dir, f))
        print("\n" + "="*40 + "\n")

if __name__ == "__main__":
    main()
