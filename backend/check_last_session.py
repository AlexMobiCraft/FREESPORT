import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freesport.settings.production')
django.setup()

from apps.products.models import ImportSession, Product, ProductVariant

def check_import_status():
    print("-" * 50)
    print("CHECKING LAST IMPORT SESSION")
    print("-" * 50)
    
    try:
        session = ImportSession.objects.latest('created_at')
        print(f"Session ID: {session.pk}")
        print(f"Status:     {session.status}")
        print(f"Created:    {session.created_at}")
        print(f"Updated:    {session.updated_at}")
        print(f"Files:      {session.import_type}")
        print("-" * 50)
        print("REPORT LOG:")
        print(session.report)
        print("-" * 50)
        
        if session.error_message:
            print(f"ERROR: {session.error_message}")
            print("-" * 50)

    except ImportSession.DoesNotExist:
        print("No import sessions found.")
        return

    print("\nDATABASE STATS:")
    print(f"Products: {Product.objects.count()}")
    print(f"Variants: {ProductVariant.objects.count()}")

if __name__ == "__main__":
    check_import_status()
