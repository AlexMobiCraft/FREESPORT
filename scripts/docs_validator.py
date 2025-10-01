#!/usr/bin/env python3
"""
Документация FREESPORT - скрипт валидации и поиска несоответствий

Использование:
    python scripts/docs_validator.py [команда]

Команды:
    validate       - полная валидация документации
    obsolete       - поиск устаревших терминов
    cross-links    - проверка кросс-ссылок
    api-coverage   - проверка покрытия API документацией
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class DocsValidator:
    """Валидатор документации FREESPORT"""

    def __init__(self, docs_root: str = "docs"):
        self.docs_root = Path(docs_root)
        self.project_root = Path(__file__).parent.parent

        # Паттерны для поиска проблем
        self.obsolete_patterns = [
            r"\bзаглушка\b",
            r"\bвременно\b",
            r"\bTODO.*[Оо]тсутствует\b",
            r"\bбудет\s+реализовано\b",
            r"\bпланируется\b",
        ]

        # Ключевые документы для проверки
        self.key_docs = [
            "index.md",
            "PRD.md",
            "api-spec.yaml",
            "api-views-documentation.md",
            "architecture.md",
        ]

    def validate_all(self) -> Dict[str, List[str]]:
        """Полная валидация документации"""
        results = {
            "errors": [],
            "warnings": [],
            "obsolete_terms": [],
            "broken_links": [],
        }

        print("🔍 Начинаем валидацию документации FREESPORT...")

        # 1. Поиск устаревших терминов
        print("📝 Поиск устаревших терминов...")
        obsolete = self.find_obsolete_terms()
        results["obsolete_terms"] = obsolete

        # 2. Проверка кросс-ссылок
        print("🔗 Проверка кросс-ссылок...")
        broken_links = self.check_cross_references()
        results["broken_links"] = broken_links

        # 3. Проверка структуры
        print("📁 Проверка структуры...")
        structure_issues = self.validate_structure()
        results["warnings"].extend(structure_issues)

        # 4. Проверка покрытия API
        print("🔌 Проверка покрытия API...")
        api_issues = self.check_api_coverage()
        results["warnings"].extend(api_issues)

        return results

    def find_obsolete_terms(self) -> List[str]:
        """Поиск устаревших терминов в документации"""
        obsolete_terms = []

        # Исключаем файлы, где устаревшие термины допустимы
        exclude_patterns = [
            "TODO_TEMPORARY_FIXES.md",  # Этот файл специально для TODO
            "implementation/",  # Здесь могут быть упоминания для контекста
        ]

        for md_file in self.docs_root.rglob("*.md"):
            # Проверяем, не в исключенной директории ли файл
            if any(excl in str(md_file) for excl in exclude_patterns):
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    for pattern in self.obsolete_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            obsolete_terms.append(
                                f"{md_file.relative_to(self.docs_root)}:{line_num}: {line.strip()}"
                            )

            except Exception as e:
                obsolete_terms.append(f"Ошибка чтения {md_file}: {e}")

        return obsolete_terms

    def check_cross_references(self) -> List[str]:
        """Проверка кросс-ссылок между документами"""
        broken_links = []
        all_files = set()

        # Собираем все файлы документации
        for md_file in self.docs_root.rglob("*.md"):
            rel_path = md_file.relative_to(self.docs_root)
            all_files.add(str(rel_path))

        # Проверяем ссылки в каждом файле
        for md_file in self.docs_root.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")

                # Ищем markdown ссылки вида [text](./path.md)
                link_pattern = r"\[([^\]]+)\]\(([^)]+)\.md\)"
                matches = re.findall(link_pattern, content)

                for text, link_path in matches:
                    # Проверяем, существует ли файл
                    if link_path not in all_files and not link_path.startswith("http"):
                        broken_links.append(
                            f"{md_file.relative_to(self.docs_root)}: "
                            f"сломанная ссылка на {link_path}.md"
                        )

            except Exception as e:
                broken_links.append(f"Ошибка чтения {md_file}: {e}")

        return broken_links

    def validate_structure(self) -> List[str]:
        """Проверка структуры документов"""
        issues = []

        # Проверяем наличие обязательных разделов в index.md
        index_path = self.docs_root / "index.md"
        if index_path.exists():
            try:
                content = index_path.read_text(encoding="utf-8")
                required_sections = [
                    "## Корневые документы",
                    "## Architecture",
                    "## Database",
                    "## Decisions",
                ]

                for section in required_sections:
                    if section not in content:
                        issues.append(f"index.md: отсутствует раздел '{section}'")

            except Exception as e:
                issues.append(f"Ошибка чтения index.md: {e}")

        return issues

    def check_api_coverage(self) -> List[str]:
        """Проверка покрытия API документацией"""
        issues = []

        # Проверяем API spec и views documentation
        api_spec = self.docs_root / "api-spec.yaml"
        api_views = self.docs_root / "api-views-documentation.md"

        if not api_spec.exists():
            issues.append("Отсутствует api-spec.yaml")
        if not api_views.exists():
            issues.append("Отсутствует api-views-documentation.md")

        return issues

    def generate_report(self, results: Dict[str, List[str]]) -> str:
        """Генерация отчета о валидации"""
        report = []
        report.append("📊 ОТЧЕТ ВАЛИДАЦИИ ДОКУМЕНТАЦИИ")
        report.append("=" * 50)

        total_issues = sum(len(issues) for issues in results.values())

        if total_issues == 0:
            report.append("✅ Документация валидна! Проблем не найдено.")
            return "\n".join(report)

        # Ошибки
        if results["errors"]:
            report.append(f"\n❌ ОШИБКИ ({len(results['errors'])}):")
            for error in results["errors"]:
                report.append(f"  • {error}")

        # Предупреждения
        if results["warnings"]:
            report.append(f"\n⚠️  ПРЕДУПРЕЖДЕНИЯ ({len(results['warnings'])}):")
            for warning in results["warnings"]:
                report.append(f"  • {warning}")

        # Устаревшие термины
        if results["obsolete_terms"]:
            report.append(f"\n📝 УСТАРЕВШИЕ ТЕРМИНЫ ({len(results['obsolete_terms'])}):")
            for term in results["obsolete_terms"][:10]:  # Показываем первые 10
                report.append(f"  • {term}")
            if len(results["obsolete_terms"]) > 10:
                report.append(
                    f"  ... и ещё {len(results['obsolete_terms']) - 10} упоминаний"
                )

        # Сломанные ссылки
        if results["broken_links"]:
            report.append(f"\n🔗 СЛОМАННЫЕ ССЫЛКИ ({len(results['broken_links'])}):")
            for link in results["broken_links"][:5]:  # Показываем первые 5
                report.append(f"  • {link}")
            if len(results["broken_links"]) > 5:
                report.append(f"  ... и ещё {len(results['broken_links']) - 5} ссылок")

        report.append(f"\n📈 ИТОГО ПРОБЛЕМ: {total_issues}")

        return "\n".join(report)


def main():
    """Основная функция"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = "validate"

    validator = DocsValidator()

    if command == "validate":
        results = validator.validate_all()
        report = validator.generate_report(results)
        print(report)

        # Возвращаем код выхода
        total_issues = sum(len(issues) for issues in results.values())
        sys.exit(0 if total_issues == 0 else 1)

    elif command == "obsolete":
        obsolete = validator.find_obsolete_terms()
        if obsolete:
            print("📝 Найденные устаревшие термины:")
            for term in obsolete:
                print(f"  • {term}")
            sys.exit(1)
        else:
            print("✅ Устаревших терминов не найдено")
            sys.exit(0)

    elif command == "cross-links":
        broken_links = validator.check_cross_references()
        if broken_links:
            print("🔗 Найденные сломанные ссылки:")
            for link in broken_links:
                print(f"  • {link}")
            sys.exit(1)
        else:
            print("✅ Все ссылки корректны")
            sys.exit(0)

    elif command == "api-coverage":
        issues = validator.check_api_coverage()
        if issues:
            print("🔌 Проблемы с покрытием API:")
            for issue in issues:
                print(f"  • {issue}")
            sys.exit(1)
        else:
            print("✅ API полностью документирован")
            sys.exit(0)

    else:
        print(f"Неизвестная команда: {command}")
        print("Доступные команды: validate, obsolete, cross-links, api-coverage")
        sys.exit(1)


if __name__ == "__main__":
    main()
