"""Repair-команда для нового контракта публичного дерева категорий."""

from __future__ import annotations

import re
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify


PLACEHOLDER_RE = re.compile(r"^Категория\s+[-0-9a-fA-F_]{8,}$")
FALLBACK_SLUG = "onec-unresolved-category"


class Command(BaseCommand):
    help = (
        "Восстанавливает якорь СПОРТ, переносит полезные root-категории под него "
        "и изолирует placeholder-категории без каскадного удаления товаров."
    )

    def add_arguments(self, parser):
        parser.add_argument("--execute", action="store_true", help="Выполнить изменения в БД")
        parser.add_argument(
            "--root-name",
            type=str,
            default=None,
            help="Имя якорной категории (override settings.ROOT_CATEGORY_NAME)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.products.models import Category, Product

        execute = bool(options.get("execute"))
        root_name = options.get("root_name") or getattr(settings, "ROOT_CATEGORY_NAME", "СПОРТ")

        anchor = Category.objects.filter(name=root_name, parent__isnull=True).first()
        placeholder_roots = list(
            Category.objects.filter(parent__isnull=True, name__startswith="Категория ").exclude(name=root_name)
        )
        placeholder_roots = [cat for cat in placeholder_roots if self._is_placeholder(cat)]
        public_roots = list(
            Category.objects.filter(parent__isnull=True)
            .exclude(name=root_name)
            .exclude(slug__in=[FALLBACK_SLUG, "uncategorized"])
        )
        public_roots = [cat for cat in public_roots if not self._is_placeholder(cat)]

        products_in_placeholders = 0
        for category in placeholder_roots:
            ids = self._descendant_ids(category)
            ids.add(category.pk)
            products_in_placeholders += Product.objects.filter(category_id__in=ids).count()

        self.stdout.write(
            "DRY-RUN"
            if not execute
            else "EXECUTE"
            + f": anchor_exists={bool(anchor)}, public_roots={len(public_roots)}, "
            + f"placeholder_roots={len(placeholder_roots)}, "
            + f"products_in_placeholders={products_in_placeholders}"
        )

        if not execute:
            return

        with transaction.atomic():
            anchor = anchor or self._create_anchor(root_name)
            fallback = self._get_fallback_category()

            public_reparented = 0
            for category in public_roots:
                if category.pk in {anchor.pk, fallback.pk}:
                    continue
                category.parent = anchor
                category.save(update_fields=["parent"])
                public_reparented += 1

            products_moved = 0
            placeholders_hidden = 0
            for category in placeholder_roots:
                ids = self._descendant_ids(category)
                ids.add(category.pk)
                products_moved += Product.objects.filter(category_id__in=ids).update(category=fallback)
                Category.objects.filter(pk__in=ids).update(is_active=False)
                if category.pk != fallback.pk:
                    category.parent = fallback
                    category.is_active = False
                    category.save(update_fields=["parent", "is_active"])
                    placeholders_hidden += 1

        self.stdout.write(
            "SUMMARY: "
            f"anchor={anchor.name}, public_reparented={public_reparented}, "
            f"placeholders_hidden={placeholders_hidden}, "
            f"products_moved_to_fallback={products_moved}"
        )

    def _is_placeholder(self, category: Any) -> bool:
        return bool(PLACEHOLDER_RE.match(category.name or ""))

    def _create_anchor(self, root_name: str) -> Any:
        from apps.products.models import Category

        slug = self._unique_slug(slugify(root_name) or "sport")
        return Category.objects.create(name=root_name, slug=slug, is_active=True)

    def _get_fallback_category(self) -> Any:
        from apps.products.models import Category

        category, _ = Category.objects.get_or_create(
            slug=FALLBACK_SLUG,
            defaults={
                "name": "Техническая категория: неразрешенные ссылки 1С",
                "onec_id": "__onec_unresolved_category__",
                "is_active": False,
            },
        )
        if category.is_active:
            category.is_active = False
            category.save(update_fields=["is_active"])
        return category

    def _unique_slug(self, base_slug: str) -> str:
        from apps.products.models import Category

        slug = base_slug
        counter = 1
        while Category.objects.filter(slug=slug).exists():
            counter += 1
            slug = f"{base_slug}-{counter}"
        return slug

    def _descendant_ids(self, category: Any) -> set[int]:
        ids: set[int] = set()
        children = category.children.all()
        for child in children:
            ids.add(child.pk)
            ids.update(self._descendant_ids(child))
        return ids
