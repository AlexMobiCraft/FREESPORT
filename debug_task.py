import os
import sys
import django

sys.path.append("/app/backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.development")
django.setup()

from apps.products.tasks import process_1c_import_task
import inspect

sig = inspect.signature(process_1c_import_task.__wrapped__)
print(f"Signature: {sig}")
print(f"Parameters: {sig.parameters.keys()}")
