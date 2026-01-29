
import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.products.models import ImportSession

print("-" * 50)
sessions = ImportSession.objects.order_by('-id')[:5]
for s in sessions:
    print(f"ID: {s.pk} | Status: {s.status} | Time: {s.updated_at}")
    print("Report Tail:")
    print(s.report[-500:] if s.report else "No report")
    print("-" * 50)
