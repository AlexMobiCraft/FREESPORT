
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freesport.settings.development')
django.setup()

from apps.products.models import Category

def fix_categories():
    sport = Category.objects.filter(name='СПОРТ').first()
    if not sport:
        print("Category 'СПОРТ' not found!")
        return
        
    target = Category.objects.filter(name='Категории для главной', parent=sport).first()
    if not target:
        target = Category.objects.create(
            name='Категории для главной',
            parent=sport,
            slug='kategorii-dlya-glavnoy',
            is_active=True
        )
        print(f"Created 'Категории для главной' (ID={target.id})")
    else:
        target.slug = 'kategorii-dlya-glavnoy'
        target.is_active = True
        target.save()
        print(f"Updated existing 'Категории для главной' (ID={target.id})")

    # Add children to see them in admin
    child_names = ['Спортивные игры', 'Спортивная одежда', 'Тренажеры']
    for name in child_names:
        child = Category.objects.filter(name=name).first()
        if child:
            child.parent = target
            child.save()
            print(f"Moved '{name}' to 'Категории для главной'")

if __name__ == "__main__":
    fix_categories()
