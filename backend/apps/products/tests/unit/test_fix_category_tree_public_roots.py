"""Тесты repair-команды публичных root-категорий."""

from __future__ import annotations

import io

import pytest
from django.core.management import call_command

from apps.products.factories import CategoryFactory, ProductFactory
from apps.products.models import Category, Product

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


def test_fix_category_tree_execute_reparents_public_roots_and_isolates_placeholders():
    sport = CategoryFactory(name="СПОРТ", slug="sport-anchor", onec_id="sport-root", parent=None)
    useful_root = CategoryFactory(name="Футбол", slug="football-root", parent=None)
    useful_product = ProductFactory(category=useful_root, create_variant=False)
    placeholder = CategoryFactory(
        name="Категория 123e4567-e89b-12d3-a456-426614174000",
        slug="category-placeholder",
        parent=None,
        is_active=True,
    )
    placeholder_product = ProductFactory(category=placeholder, create_variant=False)

    out = io.StringIO()
    call_command("fix_category_tree_public_roots", execute=True, stdout=out)

    sport.refresh_from_db()
    useful_root.refresh_from_db()
    placeholder.refresh_from_db()
    useful_product.refresh_from_db()
    placeholder_product.refresh_from_db()
    fallback = Category.objects.get(slug="onec-unresolved-category")

    assert sport.parent is None
    assert useful_root.parent == sport
    assert useful_product.category == useful_root
    assert placeholder.parent == fallback
    assert placeholder.is_active is False
    assert placeholder_product.category == fallback
    assert Product.objects.filter(pk__in=[useful_product.pk, placeholder_product.pk]).count() == 2
    assert "products_moved_to_fallback=1" in out.getvalue()


def test_fix_category_tree_execute_restores_missing_sport_anchor_without_deleting_products():
    useful_root = CategoryFactory(name="Одежда", slug="clothes-root", parent=None)
    useful_product = ProductFactory(category=useful_root, create_variant=False)

    call_command("fix_category_tree_public_roots", execute=True, stdout=io.StringIO())

    sport = Category.objects.get(name="СПОРТ", parent=None)
    useful_root.refresh_from_db()
    useful_product.refresh_from_db()

    assert sport.slug == "sport"
    assert useful_root.parent == sport
    assert useful_product.category == useful_root
