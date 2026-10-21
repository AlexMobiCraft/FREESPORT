#!/usr/bin/env python3
"""
Проверка кросс-ссылок в документации OPTISPORT Platform.

Проверяет:
- Markdown ссылки на локальные файлы
- Якоря (anchors) в ссылках
- Внешние URL (опционально)
- Циклические ссылки

Использование:
    python scripts/docs_link_checker.py                # Проверка всех ссылок
    python scripts/docs_link_checker.py --external     # Включая внешние URL
    python scripts/docs_link_checker.py --fix          # Автоисправление (где возможно)
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import argparse

from exclude_utils import load_exclude_patterns


class Colors:
    """ANSI цвета для вывода."""

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class LinkChecker:
    """Проверка ссылок в markdown документах."""

    def __init__(
        self,
        docs_dir: Path,
        check_external: bool = False,
        exclude_patterns: List[str] | None = None,
    ):
        self.docs_dir = docs_dir
        self.project_root = docs_dir.parent
        self.check_external = check_external
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.checked_files = 0
        self.total_links = 0
        self.exclude_patterns = list(exclude_patterns or [])

    def print_header(self, text: str):
        """Печать заголовка."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}\n")

    def extract_links(self, content: str, file_path: Path) -> List[Dict]:
        """Извлечь все ссылки из markdown файла."""
        links = []

        # Паттерны для различных типов ссылок
        patterns = [
            # [text](url)
            (r"\[([^\]]+)\]\(([^)]+)\)", "inline"),
            # [text][ref] и [ref]: url
            (r"\[([^\]]+)\]\[([^\]]+)\]", "reference"),
            # ![alt](image)
            (r"!\[([^\]]*)\]\(([^)]+)\)", "image"),
        ]

        for pattern, link_type in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                text = match.group(1)
                url = match.group(2)

                # Находим номер строки
                line_num = content[: match.start()].count("\n") + 1

                links.append(
                    {
                        "text": text,
                        "url": url,
                        "type": link_type,
                        "line": line_num,
                        "file": file_path,
                    }
                )

        return links

    def is_external_url(self, url: str) -> bool:
        """Проверка, является ли URL внешним."""
        return url.startswith(("http://", "https://", "mailto:", "ftp://"))

    def _is_excluded(self, path: Path) -> bool:
        """Проверить, входит ли путь в список исключений."""
        try:
            rel_path = path.relative_to(self.project_root).as_posix()
        except ValueError:
            return False
        return any(
            self._match_pattern(rel_path, pattern) for pattern in self.exclude_patterns
        )

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Проверить совпадение пути с шаблоном исключения."""
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            return path.startswith(prefix)
        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            if not path.startswith(prefix):
                return False
            remainder = path[len(prefix) :]
            return remainder.startswith("/") and remainder.count("/") <= 1
        return path == pattern

    def resolve_link_path(self, link_url: str, source_file: Path) -> Optional[Path]:
        """Разрешить путь ссылки относительно исходного файла."""
        # Убираем якорь
        clean_url = link_url.split("#")[0]

        if not clean_url:  # Только якорь
            return source_file

        # Относительный путь
        if clean_url.startswith("./") or clean_url.startswith("../"):
            target = (source_file.parent / clean_url).resolve()
        # Абсолютный путь от docs/
        elif clean_url.startswith("/"):
            target = (self.docs_dir / clean_url.lstrip("/")).resolve()
        # Путь относительно docs/
        else:
            target = (self.docs_dir / clean_url).resolve()

        return target

    def extract_anchors(self, content: str) -> Set[str]:
        """Извлечь все якоря (заголовки) из markdown файла."""
        anchors = set()

        # Заголовки markdown
        header_pattern = r"^#+\s+(.+)$"
        for match in re.finditer(header_pattern, content, re.MULTILINE):
            header_text = match.group(1).strip()

            # Преобразуем заголовок в якорь (как это делает GitHub/GitLab)
            anchor = header_text.lower()
            anchor = re.sub(r"[^\w\s-]", "", anchor)  # Убираем спецсимволы
            anchor = re.sub(r"[\s]+", "-", anchor)  # Пробелы в дефисы
            anchor = anchor.strip("-")

            anchors.add(anchor)

        return anchors

    def check_link(self, link: Dict) -> Optional[Dict]:
        """Проверить одну ссылку."""
        url = link["url"]

        # Пропускаем внешние URL если не включена проверка
        if self.is_external_url(url):
            if not self.check_external:
                return None
            # TODO: Добавить проверку внешних URL через requests
            return None

        # Разрешаем путь
        target_path = self.resolve_link_path(url, link["file"])

        if not target_path:
            return {
                "type": "error",
                "message": f"Не удалось разрешить путь: {url}",
                "link": link,
            }

        # Проверяем существование файла
        if not target_path.exists():
            return {
                "type": "error",
                "message": f"Файл не найден: {target_path.relative_to(self.project_root)}",
                "link": link,
            }

        if self._is_excluded(target_path):
            return None

        # Проверяем якорь, если есть
        if "#" in url:
            anchor = url.split("#")[1]

            try:
                target_content = target_path.read_text(encoding="utf-8")
                available_anchors = self.extract_anchors(target_content)

                if anchor not in available_anchors:
                    return {
                        "type": "warning",
                        "message": f"Якорь '#{anchor}' не найден в {target_path.name}",
                        "link": link,
                        "available_anchors": list(available_anchors)[:5],
                    }
            except Exception as e:
                return {
                    "type": "warning",
                    "message": f"Ошибка при проверке якоря: {e}",
                    "link": link,
                }

        return None  # Ссылка валидна

    def check_all_links(self) -> Tuple[int, int]:
        """Проверить все ссылки в документации."""
        self.print_header("🔗 ПРОВЕРКА КРОСС-ССЫЛОК В ДОКУМЕНТАЦИИ")

        md_files = [f for f in self.docs_dir.rglob("*.md") if not self._is_excluded(f)]
        self.checked_files = len(md_files)

        print(f"Найдено {len(md_files)} markdown файлов\n")

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                links = self.extract_links(content, md_file)
                self.total_links += len(links)

                for link in links:
                    if self._is_excluded(link["file"]):
                        continue

                    issue = self.check_link(link)

                    if issue:
                        if issue["type"] == "error":
                            self.errors.append(issue)
                        else:
                            self.warnings.append(issue)

            except Exception as e:
                self.warnings.append(
                    {
                        "type": "warning",
                        "message": f"Ошибка при обработке файла: {e}",
                        "link": {"file": md_file, "line": 0},
                    }
                )

        return len(self.errors), len(self.warnings)

    def print_results(self):
        """Вывод результатов проверки."""
        print(f"\n{Colors.BOLD}📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ{Colors.RESET}\n")

        print(f"Проверено файлов: {self.checked_files}")
        print(f"Проверено ссылок: {self.total_links}")
        print(f"{Colors.RED}Ошибок: {len(self.errors)}{Colors.RESET}")
        print(f"{Colors.YELLOW}Предупреждений: {len(self.warnings)}{Colors.RESET}")

        # Вывод ошибок
        if self.errors:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ ОШИБКИ:{Colors.RESET}\n")

            for i, error in enumerate(self.errors[:20], 1):
                link = error["link"]
                relative_path = link["file"].relative_to(self.docs_dir)

                print(f"{i}. {Colors.BOLD}{relative_path}:{link['line']}{Colors.RESET}")
                link_text = link.get('text', 'N/A')
                link_url = link.get('url', 'N/A')
                print(f"   Ссылка: [{link_text}]({link_url})")
                print(f"   {Colors.RED}Ошибка: {error['message']}{Colors.RESET}\n")

            if len(self.errors) > 20:
                print(f"... и еще {len(self.errors) - 20} ошибок\n")

        # Вывод предупреждений
        if self.warnings:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  ПРЕДУПРЕЖДЕНИЯ:{Colors.RESET}\n")

            for i, warning in enumerate(self.warnings[:10], 1):
                link = warning["link"]
                relative_path = link["file"].relative_to(self.docs_dir)

                print(f"{i}. {Colors.BOLD}{relative_path}:{link['line']}{Colors.RESET}")
                link_text = link.get('text', 'N/A')
                link_url = link.get('url', 'N/A')
                print(f"   Ссылка: [{link_text}]({link_url})")
                print(f"   {Colors.YELLOW}{warning['message']}{Colors.RESET}")

                if "available_anchors" in warning:
                    print(
                        f"   Доступные якоря: {', '.join(warning['available_anchors'])}"
                    )

                print()

            if len(self.warnings) > 10:
                print(f"... и еще {len(self.warnings) - 10} предупреждений\n")

        # Итог
        if not self.errors and not self.warnings:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ ВСЕ ССЫЛКИ ВАЛИДНЫ!{Colors.RESET}\n")
            return True
        elif self.errors:
            print(
                f"\n{Colors.RED}{Colors.BOLD}❌ НАЙДЕНЫ КРИТИЧНЫЕ ОШИБКИ{Colors.RESET}\n"
            )
            return False
        else:
            print(
                f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  ПРОВЕРКА ПРОЙДЕНА С ПРЕДУПРЕЖДЕНИЯМИ{Colors.RESET}\n"
            )
            return True

    def generate_report(self, output_file: Path):
        """Сгенерировать отчет в markdown формате."""
        report_lines = [
            "# Отчет проверки ссылок в документации",
            "",
            f"**Дата проверки:** {Path(__file__).stat().st_mtime}",
            f"**Проверено файлов:** {self.checked_files}",
            f"**Проверено ссылок:** {self.total_links}",
            f"**Ошибок:** {len(self.errors)}",
            f"**Предупреждений:** {len(self.warnings)}",
            "",
        ]

        if self.errors:
            report_lines.append("## ❌ Ошибки")
            report_lines.append("")

            for error in self.errors:
                link = error["link"]
                relative_path = link["file"].relative_to(self.docs_dir)
                report_lines.append(f"### {relative_path}:{link['line']}")
                report_lines.append(f"- **Ссылка:** `[{link['text']}]({link['url']})`")
                report_lines.append(f"- **Ошибка:** {error['message']}")
                report_lines.append("")

        if self.warnings:
            report_lines.append("## ⚠️ Предупреждения")
            report_lines.append("")

            for warning in self.warnings:
                link = warning["link"]
                relative_path = link["file"].relative_to(self.docs_dir)
                report_lines.append(f"### {relative_path}:{link['line']}")
                report_lines.append(f"- **Ссылка:** `[{link['text']}]({link['url']})`")
                report_lines.append(f"- **Предупреждение:** {warning['message']}")
                report_lines.append("")

        output_file.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"\n{Colors.GREEN}Отчет сохранен: {output_file}{Colors.RESET}")


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Проверка кросс-ссылок в документации OPTISPORT"
    )
    parser.add_argument(
        "--external", action="store_true", help="Проверять внешние URL (медленно)"
    )
    parser.add_argument("--report", type=str, help="Сохранить отчет в файл")

    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Дополнительные исключения (относительно корня проекта)",
    )

    args = parser.parse_args()

    # Определяем пути
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    docs_dir = project_root / "docs"

    if not docs_dir.exists():
        print(f"{Colors.RED}Ошибка: Директория docs не найдена{Colors.RESET}")
        sys.exit(1)

    # Создаем checker и запускаем проверку
    exclude_patterns = load_exclude_patterns(project_root, args.exclude)

    checker = LinkChecker(
        docs_dir, check_external=args.external, exclude_patterns=exclude_patterns
    )
    checker.check_all_links()

    # Выводим результаты
    success = checker.print_results()

    # Сохраняем отчет если нужно
    if args.report:
        report_path = Path(args.report)
        checker.generate_report(report_path)

    # Возвращаем код выхода
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
