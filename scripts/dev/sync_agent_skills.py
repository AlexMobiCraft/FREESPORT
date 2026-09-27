#!/usr/bin/env python3
"""
Синхронизация собственных навыков агентов FREESPORT.

Claude Code читает навыки из .claude/skills/, Codex и Devin Desktop — из .agents/skills/.
Источник — .claude/skills/: скрипт повторяет в .agents/skills/ каждый собственный навык
и удаляет оттуда собственные навыки, которых в источнике нет. Навыки BMAD (bmad*) и
Vercel (vercel-*) раскладывает по каталогам утилита `npx skills`, их скрипт не трогает.
Файлы, исключённые .gitignore (например .claude/skills/gitnexus/), не копируются.

Использование:
    python scripts/dev/sync_agent_skills.py           # Обновить .agents/skills/
    python scripts/dev/sync_agent_skills.py --check   # Только сверить (CI): код 1 при расхождении
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ".claude/skills"
TARGET = ".agents/skills"
MANAGED_PREFIXES = ("bmad", "vercel-")


def collect(base: str) -> dict[str, dict[str, Path]]:
    """Собственные навыки каталога: {навык: {путь внутри навыка: файл}}."""
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", base],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    skills: dict[str, dict[str, Path]] = {}
    for path in filter(None, listed.split("\0")):
        file = ROOT / path
        parts = Path(path).relative_to(base).parts
        if len(parts) < 2 or parts[0].startswith(MANAGED_PREFIXES) or not file.is_file():
            continue
        skills.setdefault(parts[0], {})[Path(*parts[1:]).as_posix()] = file
    return skills


def content(files: dict[str, Path]) -> dict[str, bytes]:
    # Окончания строк не сравниваем: на Windows git отдаёт CRLF, в CI — LF.
    return {rel: file.read_bytes().replace(b"\r\n", b"\n") for rel, file in files.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--check", action="store_true", help="только сверить, ничего не менять")
    args = parser.parse_args()

    source, target = collect(SOURCE), collect(TARGET)
    stale = sorted(name for name in source if name not in target or content(source[name]) != content(target[name]))
    orphans = sorted(set(target) - set(source))

    if not stale and not orphans:
        print(f"{TARGET}/ совпадает с {SOURCE}/ ({len(source)} навыков)")
        return 0

    if args.check:
        for name in stale:
            print(f"::error::{TARGET}/{name} отличается от {SOURCE}/{name}")
        for name in orphans:
            print(f"::error::{TARGET}/{name} есть, а {SOURCE}/{name} нет")
        print("Запусти `python scripts/dev/sync_agent_skills.py` и закоммить результат.")
        return 1

    for name in stale + orphans:
        shutil.rmtree(ROOT / TARGET / name, ignore_errors=True)
    for name in stale:
        for rel, file in source[name].items():
            dest = ROOT / TARGET / name / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest)
        print(f"обновлён {TARGET}/{name}")
    for name in orphans:
        print(f"удалён {TARGET}/{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
