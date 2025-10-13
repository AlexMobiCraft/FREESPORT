#!/usr/bin/env python3
"""
Скрипт валидации документации FREESPORT Platform.

Проверяет:
- Кросс-ссылки между документами
- Покрытие API endpoints документацией
- Устаревшие термины и TODO
- Структуру документов
- Актуальность дат

Использование:
    python scripts/docs_validator.py validate       # Полная валидация
    python scripts/docs_validator.py obsolete       # Поиск устаревших терминов
    python scripts/docs_validator.py cross-links    # Проверка ссылок
    python scripts/docs_validator.py api-coverage   # Покрытие API
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple
import argparse
import json

from exclude_utils import load_exclude_patterns

# Устанавливаем кодировку UTF-8 для вывода в консоли Windows
if sys.platform == 'win32':
    # Переопределяем стандартные потоки вывода для поддержки Unicode
    import locale
    import os
    # Устанавливаем кодировку UTF-8 для консоли
    os.system('chcp 65001 > nul')
    try:
        # Устанавливаем локаль с поддержкой UTF-8
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
    except locale.Error:
        # Если ru_RU.UTF-8 недоступна, пробуем C.UTF-8
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except locale.Error:
            # Если и это не сработало, оставляем по умолчанию
            pass


class Colors:
    """ANSI цвета для вывода в консоль."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class DocsValidator:
    """Валидатор документации проекта."""

    def __init__(self, project_root: Path, exclude_patterns: List[str] | None = None):
        self.project_root = project_root
        self.docs_dir = project_root / "docs"
        self.backend_dir = project_root / "backend"
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.exclude_patterns = list(exclude_patterns or [])

    def print_header(self, text: str):
        """Печать заголовка."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}\n")

    def print_error(self, message: str):
        """Печать ошибки."""
        print(f"{Colors.RED}[X] ОШИБКА: {message}{Colors.RESET}")
        self.errors.append(message)

    def print_warning(self, message: str):
        """Печать предупреждения."""
        print(f"{Colors.YELLOW}[!] ПРЕДУПРЕЖДЕНИЕ: {message}{Colors.RESET}")
        self.warnings.append(message)

    def print_info(self, message: str):
        """Печать информации."""
        print(f"{Colors.GREEN}[+] {message}{Colors.RESET}")
        self.info.append(message)

    def print_section(self, text: str):
        """Печать секции."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}[ПОИСК] {text}{Colors.RESET}")
    
    def safe_print(self, text: str, color: str = ""):
        """Безопасная печать текста с заменой проблемных символов."""
        # Заменяем все символы, которые могут вызывать проблемы с кодировкой
        clean_text = text.encode('cp1251', errors='replace').decode('cp1251')
        print(f"{color}{clean_text}{Colors.RESET}")

    def get_all_markdown_files(self) -> List[Path]:
        """Получить все markdown файлы в docs."""
        files = list(self.docs_dir.rglob("*.md"))
        return [f for f in files if not self._is_excluded(f)]

    def _is_excluded(self, file_path: Path) -> bool:
        """Проверить, входит ли файл в список исключений."""
        rel_path = file_path.relative_to(self.project_root).as_posix()
        return any(self._match_pattern(rel_path, pattern) for pattern in self.exclude_patterns)

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Проверка совпадения пути с паттерном исключения."""
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            return path.startswith(prefix)
        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            if not path.startswith(prefix):
                return False
            remainder = path[len(prefix):]
            return remainder.startswith('/') and remainder.count('/') <= 1
        return path == pattern

    def validate_cross_references(self) -> bool:
        """Проверка кросс-ссылок между документами."""
        self.print_section("Проверка кросс-ссылок между документами")

        md_files = self.get_all_markdown_files()
        all_valid = True

        # Паттерны для поиска ссылок
        link_patterns = [
            r'\[([^\]]+)\]\(([^)]+\.md[^)]*)\)',  # [text](file.md)
            r'\[([^\]]+)\]\(((?:\.\.?/)[^)]+)\)',  # [text](../file.md)
        ]

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                relative_path = md_file.relative_to(self.docs_dir)

                for pattern in link_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)

                    for match in matches:
                        link_text = match.group(1)
                        link_path = match.group(2)

                        # Убираем якоря из пути
                        clean_path = link_path.split('#')[0]

                        # Пропускаем внешние ссылки
                        if clean_path.startswith(('http://', 'https://', 'mailto:')):
                            continue

                        # Разрешаем путь относительно текущего файла
                        if clean_path.startswith('./') or clean_path.startswith('../'):
                            target_file = (md_file.parent / clean_path).resolve()
                        else:
                            target_file = (self.docs_dir / clean_path).resolve()

                        # Проверяем существование файла
                        if not target_file.exists():
                            self.print_error(
                                f"Сломанная ссылка в {relative_path}:\n"
                                f"  Ссылка: [{link_text}]({link_path})\n"
                                f"  Файл не найден: {target_file.relative_to(self.project_root)}"
                            )
                            all_valid = False

            except Exception as e:
                self.print_warning(f"Ошибка при проверке {relative_path}: {e}")

        if all_valid:
            self.print_info(f"Все кросс-ссылки валидны ({len(md_files)} файлов проверено)")

        return all_valid

    def find_obsolete_terms(self) -> bool:
        """Поиск устаревших терминов в документации."""
        self.print_section("Поиск устаревших терминов и временных заглушек")

        # Термины для поиска
        obsolete_patterns = {
            r'\bTODO\b(?!\s*TEMPORARY_FIXES)': 'TODO (требует внимания)',
            r'\bFIXME\b': 'FIXME (требует исправления)',
            r'\bзаглушка\b': 'Временная заглушка',
            r'\bвременно\b': 'Временное решение',
            r'\bfreesport_user\b': 'Устаревший DB_USER (должен быть postgres)',
            r'\bSQLite\b(?!.*шаблон)': 'SQLite (должен быть PostgreSQL)',
            r'\bустарел': 'Упоминание устаревшего',
        }

        md_files = self.get_all_markdown_files()
        found_issues = {}

        for md_file in md_files:
            # Пропускаем шаблоны AI - там TODO это норма
            if 'ai-implementation/templates' in str(md_file):
                continue

            try:
                content = md_file.read_text(encoding='utf-8')
                relative_path = md_file.relative_to(self.docs_dir)

                for pattern, description in obsolete_patterns.items():
                    matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))

                    if matches:
                        if str(relative_path) not in found_issues:
                            found_issues[str(relative_path)] = []

                        for match in matches:
                            # Находим номер строки
                            line_num = content[:match.start()].count('\n') + 1
                            line_text = content.split('\n')[line_num - 1].strip()

                            found_issues[str(relative_path)].append({
                                'line': line_num,
                                'text': line_text[:100],
                                'description': description
                            })

            except Exception as e:
                self.print_warning(f"Ошибка при проверке {relative_path}: {e}")

        # Вывод результатов
        if found_issues:
            print(f"\n{Colors.YELLOW}Найдено {len(found_issues)} файлов с потенциальными проблемами:{Colors.RESET}\n")

            for file_path, issues in found_issues.items():
                print(f"{Colors.BOLD}{file_path}{Colors.RESET} ({len(issues)} упоминаний):")
                for issue in issues[:3]:  # Показываем первые 3
                    print(f"  Строка {issue['line']}: {issue['description']}")
                    # Используем безопасную печать для текста с проблемными символами
                    self.safe_print(f"    {issue['text']}", Colors.CYAN)
                if len(issues) > 3:
                    print(f"  ... и еще {len(issues) - 3} упоминаний")
                print()

            self.print_warning(f"Найдено {sum(len(v) for v in found_issues.values())} устаревших терминов")
            return False
        else:
            self.print_info("Устаревшие термины не найдены")
            return True

    def check_api_coverage(self) -> bool:
        """Проверка покрытия API endpoints документацией."""
        self.print_section("Проверка покрытия API endpoints документацией")

        # Ищем все ViewSets и APIView в backend
        api_endpoints = self._find_api_endpoints()

        # Ищем упоминания endpoints в документации
        documented_endpoints = self._find_documented_endpoints()

        # Сравниваем
        undocumented = api_endpoints - documented_endpoints
        only_in_docs = documented_endpoints - api_endpoints

        if undocumented:
            self.print_warning(
                f"Найдено {len(undocumented)} недокументированных endpoints:\n" +
                "\n".join(f"  - {ep}" for ep in sorted(undocumented)[:10])
            )
            if len(undocumented) > 10:
                print(f"  ... и еще {len(undocumented) - 10} endpoints")

        if only_in_docs:
            self.print_warning(
                f"Найдено {len(only_in_docs)} endpoints в документации, но не в коде:\n" +
                "\n".join(f"  - {ep}" for ep in sorted(only_in_docs)[:10])
            )

        coverage = len(documented_endpoints) / len(api_endpoints) * 100 if api_endpoints else 100
        print(f"\n{Colors.BOLD}Покрытие API: {coverage:.1f}% ({len(documented_endpoints)}/{len(api_endpoints)}){Colors.RESET}")

        if coverage >= 95:
            self.print_info(f"Отличное покрытие API документацией!")
            return True
        elif coverage >= 80:
            self.print_warning(f"Хорошее покрытие, но можно улучшить")
            return True
        else:
            self.print_error(f"Недостаточное покрытие API документацией")
            return False

    def _find_api_endpoints(self) -> Set[str]:
        """Найти все API endpoints в коде."""
        endpoints: Set[str] = set()

        if not self.backend_dir.exists():
            return endpoints

        for py_file in self.backend_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception:
                continue

            parts = py_file.relative_to(self.backend_dir).parts
            is_views_module = any(part == "views" for part in parts[:-1]) or py_file.name == "views.py"

            if is_views_module:
                class_pattern = r"class\s+(\w+)\s*\(([^)]*)\)"
                for match in re.finditer(class_pattern, content):
                    class_name = match.group(1)
                    base_classes = match.group(2)
                    if any(keyword in base_classes for keyword in ("ViewSet", "APIView")):
                        endpoints.add(class_name)

            if py_file.name == "urls.py":
                router_pattern = r"router\.register\(\s*r?['\"]([^'\"]+)['\"]\s*,\s*([\w\.]+)"
                for match in re.finditer(router_pattern, content):
                    view_ref = match.group(2)
                    class_name = view_ref.split('.')[-1]
                    if class_name:
                        endpoints.add(class_name)

                path_pattern = r"(?:path|re_path)\(\s*['\"][^'\"]+['\"]\s*,\s*([\w\.]+)\.as_view"
                for match in re.finditer(path_pattern, content):
                    view_ref = match.group(1)
                    class_name = view_ref.split('.')[-1]
                    if class_name:
                        endpoints.add(class_name)

        return endpoints

    def _find_documented_endpoints(self) -> Set[str]:
        """Найти все задокументированные endpoints."""
        documented = set()

        # Проверяем api-views-documentation.md и api-spec.yaml
        api_docs = [
            self.docs_dir / "api-views-documentation.md",
            self.docs_dir / "api-spec.yaml"
        ]

        for doc_file in api_docs:
            if doc_file.exists():
                try:
                    content = doc_file.read_text(encoding='utf-8')

                    # Ищем упоминания ViewSet/APIView
                    pattern = r'(\w+(?:ViewSet|APIView))'
                    for match in re.finditer(pattern, content):
                        documented.add(match.group(1))

                except Exception:
                    pass

        return documented

    def check_dates_freshness(self) -> bool:
        """Проверка актуальности дат в документации."""
        self.print_section("Проверка актуальности дат в документации")

        date_patterns = [
            (r'Актуально на:\s*(\d{2}\.\d{2}\.\d{4})', 'Актуально на'),
            (r'Последнее обновление:\s*(\d{2}\.\d{2}\.\d{4})', 'Последнее обновление'),
            (r'\*\*Последнее обновление:\s*(\d{2}\.\d{2}\.\d{4})', 'Последнее обновление'),
        ]

        md_files = self.get_all_markdown_files()
        outdated_files = []
        current_date = datetime.now()

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                relative_path = md_file.relative_to(self.docs_dir)

                for pattern, label in date_patterns:
                    matches = re.finditer(pattern, content)

                    for match in matches:
                        date_str = match.group(1)
                        try:
                            doc_date = datetime.strptime(date_str, '%d.%m.%Y')
                            days_old = (current_date - doc_date).days

                            if days_old > 30:
                                outdated_files.append({
                                    'file': str(relative_path),
                                    'date': date_str,
                                    'days_old': days_old,
                                    'label': label
                                })

                        except ValueError:
                            pass

            except Exception:
                pass

        if outdated_files:
            print(f"\n{Colors.YELLOW}Найдено {len(outdated_files)} документов с устаревшими датами:{Colors.RESET}\n")

            for item in sorted(outdated_files, key=lambda x: x['days_old'], reverse=True)[:10]:
                print(f"  {item['file']}")
                print(f"    {item['label']}: {item['date']} ({item['days_old']} дней назад)")

            self.print_warning(f"Некоторые документы не обновлялись более 30 дней")
            return False
        else:
            self.print_info("Все даты актуальны")
            return True

    def validate_structure(self) -> bool:
        """Проверка структуры документов."""
        self.print_section("Проверка структуры документов")

        required_sections = {
            'stories': ['## Status', '## Story', '## Acceptance Criteria', '## Definition of Done'],
            'decisions': ['## Context', '## Decision', '## Consequences'],
        }

        issues_found = []

        for category, sections in required_sections.items():
            category_dir = self.docs_dir / category
            if not category_dir.exists():
                continue

            for md_file in category_dir.rglob("*.md"):
                if md_file.name in ['README.md', 'SUMMARY.md']:
                    continue

                try:
                    content = md_file.read_text(encoding='utf-8')
                    relative_path = md_file.relative_to(self.docs_dir)

                    missing_sections = []
                    for section in sections:
                        if section not in content:
                            missing_sections.append(section)

                    if missing_sections:
                        issues_found.append({
                            'file': str(relative_path),
                            'missing': missing_sections
                        })

                except Exception:
                    pass

        if issues_found:
            print(f"\n{Colors.YELLOW}Найдено {len(issues_found)} документов с неполной структурой:{Colors.RESET}\n")

            for item in issues_found[:5]:
                print(f"  {item['file']}")
                print(f"    Отсутствуют секции: {', '.join(item['missing'])}")

            self.print_warning(f"Некоторые документы не соответствуют шаблону")
            return False
        else:
            self.print_info("Структура документов соответствует шаблонам")
            return True

    def print_summary(self):
        """Печать итогового отчета."""
        self.print_header("[ОТЧЕТ] ИТОГОВЫЙ ОТЧЕТ ВАЛИДАЦИИ")

        print(f"{Colors.BOLD}Статистика:{Colors.RESET}")
        print(f"  {Colors.RED}[X] Ошибок: {len(self.errors)}{Colors.RESET}")
        print(f"  {Colors.YELLOW}[!] Предупреждений: {len(self.warnings)}{Colors.RESET}")
        print(f"  {Colors.GREEN}[+] Успешных проверок: {len(self.info)}{Colors.RESET}")

        if self.errors:
            print(f"\n{Colors.RED}{Colors.BOLD}[X] ВАЛИДАЦИЯ ПРОВАЛЕНА{Colors.RESET}")
            return False
        elif self.warnings:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}[!] ВАЛИДАЦИЯ ПРОЙДЕНА С ПРЕДУПРЕЖДЕНИЯМИ{Colors.RESET}")
            return True
        else:
            print(f"\n{Colors.GREEN}{Colors.BOLD}[+] ВАЛИДАЦИЯ УСПЕШНО ПРОЙДЕНА{Colors.RESET}")
            return True

    def run_full_validation(self) -> bool:
        """Запуск полной валидации."""
        self.print_header("[ПОИСК] ПОЛНАЯ ВАЛИДАЦИЯ ДОКУМЕНТАЦИИ FREESPORT")

        results = []
        results.append(self.validate_cross_references())
        results.append(self.find_obsolete_terms())
        results.append(self.check_api_coverage())
        results.append(self.check_dates_freshness())
        results.append(self.validate_structure())

        return self.print_summary()


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description='Валидация документации FREESPORT'
    )
    parser.add_argument('command', nargs='?', default='validate',
                        choices=['validate', 'obsolete', 'cross-links', 'api-coverage'],
                        help='Команда для выполнения')
    parser.add_argument('--exclude', nargs='*', default=[],
                        help='Дополнительные исключения (относительно корня проекта)')

    args = parser.parse_args()

    # Определяем корень проекта
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    exclude_patterns = load_exclude_patterns(project_root, args.exclude)

    validator = DocsValidator(project_root, exclude_patterns=exclude_patterns)

    command = args.command

    if command == 'validate':
        success = validator.run_full_validation()
        sys.exit(0 if success else 1)

    elif command == 'obsolete':
        validator.print_header("[ПОИСК] ПОИСК УСТАРЕВШИХ ТЕРМИНОВ")
        success = validator.find_obsolete_terms()
        sys.exit(0 if success else 1)

    elif command == 'cross-links':
        validator.print_header("[ПОИСК] ПРОВЕРКА КРОСС-ССЫЛОК")
        success = validator.validate_cross_references()
        sys.exit(0 if success else 1)

    elif command == 'api-coverage':
        validator.print_header("[ПОИСК] ПРОВЕРКА ПОКРЫТИЯ API")
        success = validator.check_api_coverage()
        sys.exit(0 if success else 1)

    else:
        print(f"{Colors.RED}Неизвестная команда: {command}{Colors.RESET}")
        print("\nИспользование:")
        print("  python scripts/docs_validator.py validate       # Полная валидация")
        print("  python scripts/docs_validator.py obsolete       # Поиск устаревших терминов")
        print("  python scripts/docs_validator.py cross-links    # Проверка ссылок")
        print("  python scripts/docs_validator.py api-coverage   # Покрытие API")
        sys.exit(1)


if __name__ == '__main__':
    main()
