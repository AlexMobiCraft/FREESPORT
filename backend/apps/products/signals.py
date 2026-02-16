"""
Signals для инвалидации кэша featured brands при изменении Brand.
"""

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Brand

FEATURED_BRANDS_CACHE_KEY = "featured_brands"


@receiver(post_save, sender=Brand)
@receiver(post_delete, sender=Brand)
def invalidate_featured_brands_cache(sender, **kwargs):
    """Очищает кэш featured brands при создании/обновлении/удалении Brand."""
    cache.delete(FEATURED_BRANDS_CACHE_KEY)
