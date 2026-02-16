"""
Tests for Featured Brands API Endpoint (Story 33.2)

Tests cover:
- AC-1: GET /api/v1/brands/featured/ returns only is_featured=True brands
- AC-1: Response fields: id, name, slug, image, website
- AC-1: List ordered by name
- AC-2: Response is cached (cache_page decorator)
- AC-3: Response fields in snake_case
- Anonymous user access (no auth required)
"""

import struct
import zlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from rest_framework.test import APIClient

from apps.products.models import Brand


def _make_png():
    """Create a minimal valid 1x1 PNG image."""
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw_data = b"\x00\xff\x00\x00"
    compressed = zlib.compress(raw_data)
    return signature + chunk(b"IHDR", ihdr_data) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


def _make_image(name="test.png"):
    return SimpleUploadedFile(name, _make_png(), content_type="image/png")


FEATURED_URL = "/api/v1/brands/featured/"


@pytest.mark.django_db
class TestFeaturedBrandsEndpoint:
    """Test GET /api/v1/brands/featured/ endpoint."""

    @pytest.fixture(autouse=True)
    def setup_brands(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.featured1 = Brand(name="Adidas", is_featured=True, image=_make_image("a.png"), website="https://adidas.com")
        self.featured1.save()
        self.featured2 = Brand(name="Nike", is_featured=True, image=_make_image("n.png"), website="https://nike.com")
        self.featured2.save()
        self.regular = Brand(name="Puma", is_featured=False)
        self.regular.save()
        self.inactive = Brand(name="Reebok", is_featured=True, is_active=False, image=_make_image("r.png"))
        self.inactive.save()

    def test_status_200_anonymous(self):
        """AC-1: Anonymous users get 200."""
        response = self.client.get(FEATURED_URL)
        assert response.status_code == 200

    def test_returns_only_featured(self):
        """AC-1: Only is_featured=True brands returned."""
        response = self.client.get(FEATURED_URL)
        names = [b["name"] for b in response.data["results"]]
        assert "Adidas" in names
        assert "Nike" in names
        assert "Puma" not in names

    def test_excludes_inactive_brands(self):
        """Featured but inactive brands are excluded."""
        response = self.client.get(FEATURED_URL)
        names = [b["name"] for b in response.data["results"]]
        assert "Reebok" not in names

    def test_ordered_by_name(self):
        """AC-1: Results ordered by name."""
        response = self.client.get(FEATURED_URL)
        names = [b["name"] for b in response.data["results"]]
        assert names == sorted(names)

    def test_response_fields(self):
        """AC-1, AC-3: Response contains required fields in snake_case."""
        response = self.client.get(FEATURED_URL)
        brand_data = response.data["results"][0]
        required_fields = {"id", "name", "slug", "image", "website"}
        assert required_fields.issubset(set(brand_data.keys()))

    def test_image_field_is_url_or_path(self):
        """AC-3: image field provides a URL or path."""
        response = self.client.get(FEATURED_URL)
        for brand_data in response.data["results"]:
            # image should be a non-empty string for featured brands
            assert brand_data["image"], f"image empty for {brand_data['name']}"

    def test_empty_when_no_featured(self):
        """Returns empty list when no featured brands exist."""
        from django.core.cache import cache
        cache.clear()
        Brand.objects.all().delete()
        Brand(name="OnlyRegular", is_featured=False).save()
        response = self.client.get(FEATURED_URL)
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_pagination_present(self):
        """Response uses standard pagination structure."""
        response = self.client.get(FEATURED_URL)
        assert "count" in response.data
        assert "results" in response.data


@pytest.mark.django_db
class TestFeaturedBrandsCaching:
    """Test caching behavior for featured brands endpoint (AC-2)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.brand = Brand(name="CachedBrand", is_featured=True, image=_make_image())
        self.brand.save()

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    )
    def test_cache_headers_present(self):
        """AC-2: Response includes caching headers from cache_page."""
        from django.core.cache import cache
        cache.clear()

        response = self.client.get(FEATURED_URL)
        assert response.status_code == 200
        # cache_page sets Cache-Control header
        cache_control = response.get("Cache-Control", "")
        assert "max-age" in cache_control

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    )
    def test_cached_response_same_content(self):
        """AC-2: Second request returns cached content."""
        from django.core.cache import cache
        cache.clear()

        response1 = self.client.get(FEATURED_URL)
        response2 = self.client.get(FEATURED_URL)
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.data == response2.data
