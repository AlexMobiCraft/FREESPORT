"""
Signals для инвалидации кэша featured brands при изменении Brand.

LIMITATION: QuerySet.update() и bulk_create/bulk_update обходят Django signals,
поэтому кэш НЕ инвалидируется при массовых операциях. Для таких случаев
необходимо вручную вызывать cache.delete(FEATURED_BRANDS_CACHE_KEY).
"""

from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .constants import FEATURED_BRANDS_CACHE_KEY
from .models import Brand


@receiver(post_save, sender=Brand)
@receiver(post_delete, sender=Brand)
def invalidate_featured_brands_cache(sender, **kwargs):
    """Очищает кэш featured brands при создании/обновлении/удалении Brand.

    Использует transaction.on_commit чтобы кэш очищался только после
    успешного коммита транзакции, предотвращая race condition когда
    параллельный запрос перезаписывает кэш со старыми данными.
    """
    transaction.on_commit(lambda: cache.delete(FEATURED_BRANDS_CACHE_KEY))
