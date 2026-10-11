"""
Разовый пересчёт ответственного менеджера у всех клиентов (эпик 42, стори 42.3).

Автоназначение 42.2 срабатывает на события: регистрацию, смену ИНН или
страны, правку правила региона. Клиенты, которых эти события не задели,
ответственного не получили — их добирает эта команда.

Когда запускать: на проде после распределения регионов в «Правилах
маршрутизации менеджеров», сначала с ``--dry-run``, затем без него:

    python manage.py recalculate_responsible_managers --dry-run
    python manage.py recalculate_responsible_managers

Логику назначения команда не дублирует: ответственного даёт
``resolve_responsible_for_key`` (42.2), с кэшем по ключу региона, поэтому
число запросов зависит от числа ключей, а не клиентов.

Запись — через ``QuerySet.update()``: хук автоназначения ``User.save()`` здесь
не нужен, а ``updated_at`` не трогается, чтобы тысячи записей не выглядели
изменёнными. Ручные назначения и учётные записи сотрудников не меняются.
Без активного резервного правила с менеджером команда не запускается:
клиенты регионов без правила остались бы без ответственного.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.common.models import ManagerRoutingRule
from apps.common.regions import REGION_NAMES, region_name
from apps.users.models import User
from apps.users.services.responsible_manager import (
    SOURCE_COUNTRY,
    SOURCE_FALLBACK,
    SOURCE_NONE,
    SOURCE_REGION,
    RegionKey,
    ResponsibleResolution,
    region_key,
    resolve_responsible_for_key,
)
from apps.users.staff_roles import staff_accounts_q

logger = logging.getLogger(__name__)

NO_FALLBACK_MESSAGE = (
    "Нет активного резервного правила с менеджером. Назначьте руководителя в резервном правиле "
    "и запустите снова; для оценки — --dry-run."
)

READ_CHUNK_SIZE = 2000
UPDATE_CHUNK_SIZE = 1000

COUNTER_BY_SOURCE = {
    SOURCE_REGION: "by_region",
    SOURCE_COUNTRY: "by_country",
    SOURCE_FALLBACK: "by_fallback",
}


class Command(BaseCommand):
    help = "Разовый пересчёт ответственного менеджера для всех клиентов по правилам регионов"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Посчитать и вывести отчёт, ничего не меняя",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]

        # Проверка резерва — до чтения клиентов, чтобы ничего не обнулить.
        fallback = resolve_responsible_for_key(None)
        if fallback.source == SOURCE_NONE and not dry_run:
            raise CommandError(NO_FALLBACK_MESSAGE)

        counters = dict.fromkeys(
            ("checked", "by_region", "by_country", "by_fallback", "manual", "unchanged", "no_manager"), 0
        )
        fallback_codes: Counter[str] = Counter()
        pending: defaultdict[int, list[int]] = defaultdict(list)
        cache: dict[RegionKey | None, ResponsibleResolution] = {None: fallback}

        clients = (
            User.objects.exclude(staff_accounts_q())
            .only("id", "country", "tax_id", "responsible_manager", "responsible_manager_manual")
            .order_by("pk")
            .iterator(chunk_size=READ_CHUNK_SIZE)
        )
        for client in clients:
            counters["checked"] += 1
            if client.responsible_manager_manual:
                counters["manual"] += 1
                continue

            key = region_key(client.country, client.tax_id)
            if key not in cache:
                cache[key] = resolve_responsible_for_key(key)
            resolution = cache[key]

            # manager пуст ровно тогда, когда source == SOURCE_NONE: резерва с менеджером нет.
            if resolution.manager is None:
                counters["no_manager"] += 1
                continue

            if (
                resolution.source == SOURCE_FALLBACK
                and key is not None
                and key[0] == ManagerRoutingRule.MATCH_INN_REGION
            ):
                fallback_codes[key[1]] += 1

            target_id = resolution.manager.pk
            if client.responsible_manager_id == target_id:
                counters["unchanged"] += 1
                continue
            counters[COUNTER_BY_SOURCE[resolution.source]] += 1
            pending[target_id].append(client.pk)

        if not dry_run:
            with transaction.atomic():
                for target_id, ids in pending.items():
                    for start in range(0, len(ids), UPDATE_CHUNK_SIZE):
                        # Повтор условия: ручное назначение, сделанное во время прогона, не затирается.
                        User.objects.filter(
                            pk__in=ids[start : start + UPDATE_CHUNK_SIZE],
                            responsible_manager_manual=False,
                        ).update(responsible_manager_id=target_id)

        self._write_report(counters, fallback_codes, dry_run)
        if fallback.source == SOURCE_NONE:
            self.stderr.write(self.style.WARNING(NO_FALLBACK_MESSAGE))

        logger.info(
            "Responsible managers recalculated",
            extra={"action": "responsible_manager_recalculate", "dry_run": dry_run, **counters},
        )

    def _write_report(self, counters: dict[str, int], fallback_codes: Counter[str], dry_run: bool) -> None:
        title = "Пересчёт ответственных менеджеров"
        if dry_run:
            title += " (пробный запуск, изменения не сохранены)"
        lines = [
            title,
            f"Проверено клиентов: {counters['checked']}",
            f"Назначено по коду региона: {counters['by_region']}",
            f"Назначено по стране: {counters['by_country']}",
            f"Ушло на резервное правило: {counters['by_fallback']}",
            f"Пропущено (назначен вручную): {counters['manual']}",
            f"Без изменений: {counters['unchanged']}",
        ]
        if counters["no_manager"]:
            lines.append(f"Без ответственного (нет резервного правила с менеджером): {counters['no_manager']}")
        if fallback_codes:
            lines.append("Коды без менеджера, клиенты ушли на резерв:")
            for code, count in sorted(fallback_codes.items(), key=lambda item: (-item[1], item[0])):
                label = f"{code} — {region_name(code)}" if code in REGION_NAMES else code
                lines.append(f"  {label}: {count}")
        for line in lines:
            self.stdout.write(line)
