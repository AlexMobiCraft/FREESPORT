#!/usr/bin/env python3
"""
Генератор индекса документации FREESPORT Platform.

Автоматически сканирует docs/ и обновляет:
- docs/index.md - главный индекс
- README.md в каждой поддиректории
- Статистику документации

Использование:
    python scripts/docs_index_generator.py              # Обновить все индексы
    python scripts/docs_index_generator.py --dry-run    # Показать изменения без записи
    python scripts/docs_index_generator.py --stats      # Только статистика
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Iterator
import argparse
from datetime import datetime

from exclude_utils import load_exclude_patterns


class Colors:
    """ANSI цвета для вывода."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class DocsIndexGenerator:
    """Генератор индекса документации."""

    def __init__(self, docs_dir: Path, dry_run: bool = False, exclude_patterns: List[str] | None = None):
        self.docs_dir = docs_dir
        self.project_root = docs_dir.parent
        self.dry_run = dry_run
        self.total_files = 0
        self.total_size = 0
        self.stats_by_category: Dict[str, int] = {}
        self.last_updated = datetime.now().strftime('%d.%m.%Y')
        self.exclude_patterns = list(exclude_patterns or [])

    def print_header(self, text: str):
        """Печать заголовка."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}\n")

    def extract_title(self, md_file: Path) -> str:
        """Извлечь заголовок из markdown файла."""
        try:
            content = md_file.read_text(encoding='utf-8')

            # Ищем первый заголовок H1
            match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if match:
                return match.group(1).strip()

            # Если нет H1, используем имя файла
            return md_file.stem.replace('-', ' ').replace('_', ' ').title()

        except Exception:
            return md_file.stem

    def extract_description(self, md_file: Path, max_length: int = 200) -> str:
        """Извлечь краткое описание из файла."""
        try:
            content = md_file.read_text(encoding='utf-8')

            # Пропускаем заголовок и метаданные
            lines = content.split('\n')
            description_lines = []

            skip_metadata = False
            found_content = False

            for line in lines:
                # Пропускаем frontmatter
                if line.strip() == '---':
                    skip_metadata = not skip_metadata
                    continue

                if skip_metadata:
                    continue

                # Пропускаем заголовки
                if line.startswith('#'):
                    found_content = True
                    continue

                # Собираем текст
                if found_content and line.strip():
                    description_lines.append(line.strip())

                    if len(' '.join(description_lines)) > max_length:
                        break

            description = ' '.join(description_lines)

            # Обрезаем до max_length
            if len(description) > max_length:
                description = description[:max_length].rsplit(' ', 1)[0] + '...'

            return description

        except Exception:
            return ""

    def scan_directory(self, directory: Path) -> List[Dict]:
        """Сканировать директорию и собрать информацию о файлах."""
        files_info = []

        md_files = sorted(self._iter_markdown_files(directory))

        for md_file in md_files:
            # Пропускаем служебные файлы
            if md_file.name in ['README.md', 'index.md', 'SUMMARY.md']:
                continue

            title = self.extract_title(md_file)
            description = self.extract_description(md_file)
            size = md_file.stat().st_size

            files_info.append({
                'file': md_file,
                'name': md_file.name,
                'title': title,
                'description': description,
                'size': size,
                'relative_path': md_file.relative_to(self.docs_dir)
            })

            self.total_files += 1
            self.total_size += size

        return files_info

    def _is_excluded(self, path: Path) -> bool:
        """Проверить, находится ли путь в списке исключений."""
        try:
            rel_path = path.relative_to(self.project_root).as_posix()
        except ValueError:
            return False
        return any(self._match_pattern(rel_path, pattern) for pattern in self.exclude_patterns)

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Проверить совпадение пути с шаблоном исключения."""
        if pattern.endswith('/**'):
            prefix = pattern[:-3]
            return path.startswith(prefix)
        if pattern.endswith('/*'):
            prefix = pattern[:-2]
            if not path.startswith(prefix):
                return False
            remainder = path[len(prefix):]
            return remainder.startswith('/') and remainder.count('/') <= 1
        return path == pattern

    def _iter_markdown_files(self, directory: Path) -> Iterator[Path]:
        """Итерация по Markdown файлам в директории с учетом исключений."""
        for md_file in directory.glob("*.md"):
            if self._is_excluded(md_file):
                continue
            yield md_file

    def generate_category_index(self, category_dir: Path, files: List[Dict]) -> str:
        """Сгенерировать индекс для категории."""
        category_name = category_dir.name.replace('-', ' ').replace('_', ' ').title()

        lines = [
            f"# {category_name}",
            "",
            f"Документы в категории `{category_dir.name}/`",
            "",
            f"**Всего документов:** {len(files)}",
            "",
            "---",
            ""
        ]

        # Группируем файлы по префиксам (для stories)
        if category_dir.name.startswith('epic-'):
            grouped = self._group_by_prefix(files)

            for prefix, group_files in grouped.items():
                if prefix:
                    lines.append(f"## {prefix}")
                    lines.append("")

                for file_info in group_files:
                    lines.append(f"### [{file_info['title']}](./{file_info['name']})")
                    lines.append("")
                    if file_info['description']:
                        lines.append(file_info['description'])
                        lines.append("")

        else:
            # Обычный список
            for file_info in files:
                lines.append(f"## [{file_info['title']}](./{file_info['name']})")
                lines.append("")
                if file_info['description']:
                    lines.append(file_info['description'])
                    lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(f"**Последнее обновление:** {self.last_updated}")

        return '\n'.join(lines)

    def _group_by_prefix(self, files: List[Dict]) -> Dict[str, List[Dict]]:
        """Группировать файлы по префиксам (например, 3.1, 3.2)."""
        groups = {}

        for file_info in files:
            # Ищем паттерн типа "3.1.1" или "2.3"
            match = re.match(r'^(\d+\.\d+)', file_info['name'])

            if match:
                prefix = match.group(1)
                if prefix not in groups:
                    groups[prefix] = []
                groups[prefix].append(file_info)
            else:
                if '' not in groups:
                    groups[''] = []
                groups[''].append(file_info)

        return dict(sorted(groups.items()))

    def update_main_index(self):
        """Обновить главный индекс docs/index.md."""
        self.print_header("📝 ОБНОВЛЕНИЕ ГЛАВНОГО ИНДЕКСА")

        categories = {
            'architecture': 'Архитектура',
            'decisions': 'Решения',
            'stories': 'Истории',
            'prd': 'PRD',
            'database': 'База данных',
            'qa': 'QA',
            'epics': 'Эпики',
            'implementation': 'Имплементация',
            'releases': 'Релизы'
        }

        category_stats: Dict[str, Dict[str, object]] = {}
        self.stats_by_category = {}

        for category_dir_name, category_title in categories.items():
            category_path = self.docs_dir / category_dir_name

            if not category_path.exists() or not category_path.is_dir():
                continue

            files = self.scan_directory(category_path)

            subdirs_count = sum(
                1
                for file_path in category_path.rglob("*.md")
                if not self._is_excluded(file_path)
            )

            category_stats[category_dir_name] = {
                'title': category_title,
                'count': subdirs_count,
                'files': files
            }

            self.stats_by_category[category_dir_name] = subdirs_count

        index_file = self.docs_dir / "index.md"

        if not index_file.exists():
            print(f"{Colors.YELLOW}⚠️  Файл index.md не найден{Colors.RESET}")
            return

        content = index_file.read_text(encoding='utf-8')
        stats_section = self._generate_stats_section(category_stats)

        stats_pattern = r'## Статистика документации.*?(?=##|\Z)'
        if re.search(stats_pattern, content, re.DOTALL):
            content = re.sub(stats_pattern, stats_section, content, flags=re.DOTALL)
        else:
            if not content.endswith("\n"):
                content += "\n"
            content += f"\n{stats_section}"

        date_pattern = r'\*\*Последнее обновление:\*\* \d{2}\.\d{2}\.\d{4}'
        content = re.sub(
            date_pattern,
            f"**Последнее обновление:** {self.last_updated}",
            content
        )

        if not self.dry_run:
            index_file.write_text(content, encoding='utf-8')
            print(f"{Colors.GREEN}✅ Обновлен: {index_file.relative_to(self.project_root)}{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}[DRY RUN] Будет обновлен: {index_file.relative_to(self.project_root)}{Colors.RESET}")

    def _generate_stats_section(self, category_stats: Dict[str, Dict[str, object]]) -> str:
        """Сгенерировать секцию статистики."""
        lines = [
            "## Статистика документации",
            ""
        ]

        for category, info in sorted(category_stats.items()):
            lines.append(f"- **{info['title']}:** {info['count']} документов")

        lines.append("")
        lines.append("## Навигация по проекту")

        return '\n'.join(lines)

    def update_category_readmes(self):
        """Обновить README.md в каждой категории."""
        self.print_header("📚 ОБНОВЛЕНИЕ README В КАТЕГОРИЯХ")

        categories = ['architecture', 'decisions', 'stories', 'prd', 'epics']

        for category_name in categories:
            category_dir = self.docs_dir / category_name

            if not category_dir.exists():
                continue

            # Обрабатываем подкаталоги (например, epic-1, epic-2)
            for subdir in category_dir.iterdir():
                if subdir.is_dir():
                    if self._is_excluded(subdir):
                        continue
                    files = self.scan_directory(subdir)

                    if files:
                        readme_content = self.generate_category_index(subdir, files)
                        readme_file = subdir / "README.md"

                        if not self.dry_run:
                            readme_file.write_text(readme_content, encoding='utf-8')
                            print(f"{Colors.GREEN}✅ Создан/обновлен: {readme_file.relative_to(self.docs_dir)}{Colors.RESET}")
                        else:
                            print(f"{Colors.YELLOW}[DRY RUN] Будет обновлен: {readme_file.relative_to(self.docs_dir)}{Colors.RESET}")

    def print_statistics(self):
        """Вывести статистику документации."""
        self.print_header("📊 СТАТИСТИКА ДОКУМЕНТАЦИИ")

        print(f"{Colors.BOLD}Общая информация:{Colors.RESET}")
        print(f"  Всего файлов: {self.total_files}")
        print(f"  Общий размер: {self.total_size / 1024:.1f} KB")
        print(f"  Дата обновления: {self.last_updated}")

        if self.stats_by_category:
            print(f"\n{Colors.BOLD}По категориям:{Colors.RESET}")
            for category, count in sorted(self.stats_by_category.items()):
                print(f"  {category}: {count} файлов")

    def run(self, stats_only: bool = False):
        """Запустить генерацию индексов."""
        if stats_only:
            # Только сканируем и показываем статистику
            for category_dir in self.docs_dir.iterdir():
                if category_dir.is_dir():
                    if self._is_excluded(category_dir):
                        continue
                    self.scan_directory(category_dir)
            self.print_statistics()
        else:
            # Полное обновление
            self.update_main_index()
            self.update_category_readmes()
            self.print_statistics()

            if not self.dry_run:
                print(f"\n{Colors.GREEN}{Colors.BOLD}✅ ИНДЕКСЫ УСПЕШНО ОБНОВЛЕНЫ{Colors.RESET}\n")
            else:
                print(f"\n{Colors.YELLOW}{Colors.BOLD}[DRY RUN] Изменения не применены{Colors.RESET}\n")


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description='Генератор индекса документации FREESPORT'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Показать изменения без записи в файлы'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Показать только статистику'
    )
    parser.add_argument(
        '--exclude',
        nargs='*',
        default=[],
        help='Дополнительные исключения (относительно корня проекта)'
    )

    args = parser.parse_args()

    # Определяем пути
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    docs_dir = project_root / "docs"

    if not docs_dir.exists():
        print(f"{Colors.RED}Ошибка: Директория docs не найдена{Colors.RESET}")
        sys.exit(1)

    # Создаем генератор и запускаем
    exclude_patterns = load_exclude_patterns(project_root, args.exclude)

    generator = DocsIndexGenerator(docs_dir, dry_run=args.dry_run, exclude_patterns=exclude_patterns)
    generator.run(stats_only=args.stats)

    sys.exit(0)


if __name__ == '__main__':
    main()
