#!/usr/bin/env python3
"""
Синхронизация документации OPTISPORT Platform.

Функции:
- sync_api_spec_with_views()  — сравнение API (ViewSet/APIView) в коде с документацией
- sync_decisions_with_code()  — сверка архитектурных решений с кодовой базой
- update_index()              — обновление индексов документации через docs_index_generator

Использование:
    python scripts/docs_sync.py api-sync           # Синхронизация API ↔ Views (отчет)
    python scripts/docs_sync.py decisions-sync     # Проверка соответствия решений
    python scripts/docs_sync.py update-index       # Обновление индексов документации
    python scripts/docs_sync.py all                # Выполнить все шаги

Параметры:
    --apply   — применить изменения, где поддерживается (по умолчанию только отчет)
    --exclude — пути-исключения (от корня проекта), поддерживает /** и /*
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

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


def _print_header(text: str) -> None:
    """Печатает заголовок секции в консоль."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}\n")


def _is_excluded(project_root: Path, path: Path, patterns: List[str]) -> bool:
    """Проверяет, исключен ли путь на основании шаблонов исключений."""
    try:
        rel = path.relative_to(project_root).as_posix()
    except ValueError:
        return False

    def match(p: str, pat: str) -> bool:
        if pat.endswith("/**"):
            prefix = pat[:-3]
            return p.startswith(prefix)
        if pat.endswith("/*"):
            prefix = pat[:-2]
            if not p.startswith(prefix):
                return False
            remainder = p[len(prefix) :]
            return remainder.startswith("/") and remainder.count("/") <= 1
        return p == pat

    return any(match(rel, pat) for pat in patterns)


def _collect_api_endpoints(
    backend_dir: Path, project_root: Path, exclude_patterns: List[str]
) -> Set[str]:
    """Сканирует backend и возвращает множество имен классов ViewSet/APIView.

    Ищет в модулях `views.py`, директориях `views/`, а также в `urls.py` регистрации DRF router и as_view.
    """
    endpoints: Set[str] = set()
    excluded_dirs = {"venv", "htmlcov", ".mypy_cache", "__pycache__"}

    if not backend_dir.exists():
        return endpoints

    for py in backend_dir.rglob("*.py"):
        if py.name == "__init__.py":
            continue
        parts = None
        try:
            parts = py.relative_to(backend_dir).parts
        except Exception:
            continue
        if any(part in excluded_dirs for part in parts):
            continue
        if "apps" not in parts:
            continue
        if _is_excluded(project_root, py, exclude_patterns):
            continue

        try:
            content = py.read_text(encoding="utf-8")
        except Exception:
            continue

        is_views_module = any(p == "views" for p in parts[:-1]) or py.name == "views.py"
        if is_views_module:
            class_pattern = r"class\s+(\w+)\s*\(([^)]*)\)"
            for m in re.finditer(class_pattern, content):
                class_name = m.group(1)
                base_classes = m.group(2)
                if any(b in base_classes for b in ("ViewSet", "APIView")):
                    endpoints.add(class_name)

        if py.name == "urls.py":
            router_pattern = (
                r"router\.register\(\s*r?['\"]([^'\"]+)['\"]\s*,\s*([\w\.]+)"
            )
            for m in re.finditer(router_pattern, content):
                view_ref = m.group(2)
                class_name = view_ref.split(".")[-1]
                if class_name:
                    endpoints.add(class_name)

            path_pattern = (
                r"(?:path|re_path)\(\s*['\"][^'\"]+['\"]\s*,\s*([\w\.]+)\.as_view"
            )
            for m in re.finditer(path_pattern, content):
                view_ref = m.group(1)
                class_name = view_ref.split(".")[-1]
                if class_name:
                    endpoints.add(class_name)

    return endpoints


def _collect_doc_endpoints(docs_dir: Path) -> Set[str]:
    """Сканирует ключевые документы API и возвращает набор упомянутых классов ViewSet/APIView."""
    documented: Set[str] = set()
    candidates = [docs_dir / "api-views-documentation.md", docs_dir / "api-spec.yaml"]
    for f in candidates:
        if not f.exists():
            continue
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in re.finditer(r"(\w+(?:ViewSet|APIView|View))", content):
            documented.add(m.group(1))
    return documented


def sync_api_spec_with_views(
    project_root: Path, apply: bool, exclude_patterns: List[str]
) -> Tuple[Set[str], Set[str]]:
    """Синхронизирует API спецификацию с кодом представлений.

    - Собирает список эндпоинтов из кода (`backend/`).
    - Собирает список задокументированных эндпоинтов из `docs/`.
    - Печатает расхождения. При `apply=True` может дописывать подсказки в `docs/api-views-documentation.md`.
    """
    _print_header("🔄 СИНХРОНИЗАЦИЯ API SPEC ↔ VIEWS")

    backend_dir = project_root / "backend"
    docs_dir = project_root / "docs"

    code_eps = _collect_api_endpoints(backend_dir, project_root, exclude_patterns)
    doc_eps = _collect_doc_endpoints(docs_dir)

    undocumented = sorted(code_eps - doc_eps)
    stale = sorted(doc_eps - code_eps)

    print(f"Найдено в коде: {len(code_eps)}; в документации: {len(doc_eps)}")
    if undocumented:
        print(
            f"{Colors.YELLOW}Недокументированные классы ({len(undocumented)}):{Colors.RESET}"
        )
        for name in undocumented[:25]:
            print(f"  - {name}")
        if len(undocumented) > 25:
            print(f"  ... и еще {len(undocumented) - 25}")
    else:
        print(f"{Colors.GREEN}Все классы покрыты документацией{Colors.RESET}")

    if stale:
        print(
            f"{Colors.YELLOW}Есть классы в документации, не найденные в коде ({len(stale)}):{Colors.RESET}"
        )
        for name in stale[:25]:
            print(f"  - {name}")
        if len(stale) > 25:
            print(f"  ... и еще {len(stale) - 25}")

    # При применении — дописываем подсказочную секцию в конец api-views-documentation.md
    if apply and undocumented:
        target = docs_dir / "api-views-documentation.md"
        if target.exists():
            try:
                with target.open("a", encoding="utf-8") as f:
                    f.write("\n\n---\n\n")
                    f.write("## Список эндпоинтов, требующих документирования\n\n")
                    for name in undocumented:
                        f.write(f"- [ ] {name}\n")
                print(
                    f"{Colors.GREEN}Добавлены пункты для документирования в {target.relative_to(project_root)}{Colors.RESET}"
                )
            except Exception as e:
                print(
                    f"{Colors.RED}Ошибка при обновлении {target.name}: {e}{Colors.RESET}"
                )
        else:
            print(
                f"{Colors.YELLOW}Файл {target.relative_to(project_root)} не найден, пропуск автодобавления{Colors.RESET}"
            )

    return set(undocumented), set(stale)


def _extract_decision_ids(decisions_dir: Path) -> Set[str]:
    """Извлекает идентификаторы решений (по схеме файлов, например story-2.1-*, decision-*)."""
    ids: Set[str] = set()
    if not decisions_dir.exists():
        return ids
    for md in decisions_dir.glob("*.md"):
        stem = md.stem
        # Примеры: story-2.1-api-documentation-decisions, decision-2024-10-db-user
        m = re.match(r"([a-z]+[-\d\.]+).*", stem)
        if m:
            ids.add(m.group(1))
    return ids


def _scan_code_for_decision_refs(
    project_root: Path, exclude_patterns: List[str]
) -> Set[str]:
    """Грубый поиск упоминаний идентификаторов решений в коде (по строковым вхождениям)."""
    refs: Set[str] = set()
    for py in (project_root / "backend").rglob("*.py"):
        if _is_excluded(project_root, py, exclude_patterns):
            continue
        try:
            content = py.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in re.finditer(
            r"(story-\d+\.\d+|decision-\d{4}-\d{2}-[\w-]+)", content, re.IGNORECASE
        ):
            refs.add(m.group(1))
    return refs


def sync_decisions_with_code(
    project_root: Path, apply: bool, exclude_patterns: List[str]
) -> Tuple[Set[str], Set[str]]:
    """Сверяет документы из `docs/decisions/` с упоминаниями в коде.

    Возвращает кортеж (unreferenced, missing_in_docs):
    - unreferenced — решения, которые есть в docs, но не упоминаются в коде;
    - missing_in_docs — идентификаторы, упомянутые в коде, но не найдено документа.

    При `apply=True` добавляет чек-лист в `docs/decisions/README.md` при наличии каталога.
    """
    _print_header("🧭 СИНХРОНИЗАЦИЯ РЕШЕНИЙ ↔ КОД")

    decisions_dir = project_root / "docs" / "decisions"

    doc_ids = _extract_decision_ids(decisions_dir)
    code_refs = _scan_code_for_decision_refs(project_root, exclude_patterns)

    unreferenced = sorted(doc_ids - code_refs)
    missing_in_docs = sorted(code_refs - doc_ids)

    print(f"В документах решений: {len(doc_ids)}; упоминаний в коде: {len(code_refs)}")
    if unreferenced:
        print(
            f"{Colors.YELLOW}Решения без упоминаний в коде ({len(unreferenced)}):{Colors.RESET}"
        )
        for i in unreferenced[:20]:
            print(f"  - {i}")
        if len(unreferenced) > 20:
            print(f"  ... и еще {len(unreferenced) - 20}")
    else:
        print(
            f"{Colors.GREEN}Все решения имеют упоминания в коде или не требуют их{Colors.RESET}"
        )

    if missing_in_docs:
        print(
            f"{Colors.YELLOW}Идентификаторы, упомянутые в коде, но отсутствующие в docs ({len(missing_in_docs)}):{Colors.RESET}"
        )
        for i in missing_in_docs[:20]:
            print(f"  - {i}")
        if len(missing_in_docs) > 20:
            print(f"  ... и еще {len(missing_in_docs) - 20}")

    if apply and missing_in_docs:
        readme = decisions_dir / "README.md"
        if decisions_dir.exists() and readme.exists():
            try:
                with readme.open("a", encoding="utf-8") as f:
                    f.write("\n\n---\n\n")
                    f.write("## Требуют оформления документов\n\n")
                    for i in missing_in_docs:
                        f.write(f"- [ ] {i}\n")
                print(
                    f"{Colors.GREEN}Добавлены чек-листы в {readme.relative_to(project_root)}{Colors.RESET}"
                )
            except Exception as e:
                print(f"{Colors.RED}Ошибка при обновлении README: {e}{Colors.RESET}")
        else:
            print(
                f"{Colors.YELLOW}Каталог или README для решений не найден — пропуск автодобавления{Colors.RESET}"
            )

    return set(unreferenced), set(missing_in_docs)


def _load_docs_index_generator(project_root: Path):
    """Динамически загружает модуль `docs_index_generator.py` и возвращает класс DocsIndexGenerator.

    Это позволяет использовать реализованную логику без дублирования кода и без изменения PYTHONPATH.
    """
    script_path = project_root / "scripts" / "docs_index_generator.py"
    spec = importlib.util.spec_from_file_location("docs_index_generator", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Не удалось загрузить docs_index_generator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    if not hasattr(module, "DocsIndexGenerator"):
        raise RuntimeError("В docs_index_generator.py не найден DocsIndexGenerator")
    return module.DocsIndexGenerator


def update_index(
    project_root: Path, dry_run: bool, exclude_patterns: List[str]
) -> None:
    """Обновляет индексы документации, используя `DocsIndexGenerator` из существующего скрипта.

    Выполняет обновление главного индекса, README по категориям и печатает статистику.
    """
    _print_header("📝 ОБНОВЛЕНИЕ ИНДЕКСОВ ДОКУМЕНТАЦИИ")
    docs_dir = project_root / "docs"
    if not docs_dir.exists():
        print(f"{Colors.RED}Ошибка: директория docs не найдена{Colors.RESET}")
        sys.exit(1)

    DocsIndexGenerator = _load_docs_index_generator(project_root)
    generator = DocsIndexGenerator(
        docs_dir, dry_run=dry_run, exclude_patterns=exclude_patterns
    )
    generator.run(stats_only=False)


def main() -> None:
    """Точка входа CLI для синхронизации документации."""
    parser = argparse.ArgumentParser(description="Синхронизация документации OPTISPORT")
    parser.add_argument(
        "command",
        choices=["api-sync", "decisions-sync", "update-index", "all"],
        help="Команда для выполнения",
    )
    parser.add_argument(
        "--apply", action="store_true", help="Применять изменения (где поддерживается)"
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Дополнительные исключения (относительно корня проекта)",
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    exclude_patterns = load_exclude_patterns(project_root, args.exclude)

    if args.command in ("api-sync", "all"):
        sync_api_spec_with_views(
            project_root, apply=args.apply, exclude_patterns=exclude_patterns
        )
    if args.command in ("decisions-sync", "all"):
        sync_decisions_with_code(
            project_root, apply=args.apply, exclude_patterns=exclude_patterns
        )
    if args.command in ("update-index", "all"):
        # Для update-index используем apply как обратный dry_run
        update_index(
            project_root, dry_run=not args.apply, exclude_patterns=exclude_patterns
        )


if __name__ == "__main__":
    main()
