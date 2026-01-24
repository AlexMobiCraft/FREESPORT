import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesport.settings.development")
django.setup()

from apps.products.tasks import process_1c_import_task
import inspect

func = process_1c_import_task.__wrapped__
print(f"Source:\n{inspect.getsource(func)}")
