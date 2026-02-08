import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.production")
django.setup()

from apps.products.models import ImportSession

count = ImportSession.objects.filter(status="pending").update(
    status="failed", error_message="Stuck session cleared after Celery restart"
)
print(f"Cleared {count} stuck sessions.")
