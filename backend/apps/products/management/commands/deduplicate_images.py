"""
Management команда для удаления дублированных и мелких изображений в базе данных.

Использование:
    python manage.py deduplicate_images                  # Очистка всех дублей
    python manage.py deduplicate_images --dry-run       # Тестовый запуск
    python manage.py deduplicate_images --verbose       # Подробный вывод
    python manage.py deduplicate_images --min-size 100  # Удалить файлы меньше 100KB

Описание проблемы:
    Из-за бага в импорте, одно изображение могло сохраняться с разными путями:
    - products/base/import_files/41cae745...jpg
    - products/base/41/41cae745...jpg
    
    Эта команда удаляет дубликаты, оставляя только первый путь для каждого уникального filename.
    Также удаляет изображения меньше указанного размера (по умолчанию 100KB).
"""

import logging
import os
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from tqdm import tqdm

from apps.products.models import Product, ProductVariant

logger = logging.getLogger(__name__)

# Минимальный размер файла в KB (по умолчанию 100KB)
DEFAULT_MIN_SIZE_KB = 100


class Command(BaseCommand):
    """Удаление дублированных путей изображений в Product и ProductVariant."""

    help = "Удаление дублированных и мелких изображений в базе данных"

    def add_arguments(self, parser):
        """Добавление аргументов командной строки."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Тестовый запуск без записи изменений в базу",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Подробный вывод обнаруженных дублей",
        )
        parser.add_argument(
            "--prefer-new-path",
            action="store_true",
            help="Предпочитать новый формат пути (XX/...) вместо старого (import_files/...)",
        )
        parser.add_argument(
            "--min-size",
            type=int,
            default=DEFAULT_MIN_SIZE_KB,
            help=f"Минимальный размер файла в KB (по умолчанию {DEFAULT_MIN_SIZE_KB}KB). "
                 f"Файлы меньше этого размера будут удалены из списка.",
        )
        parser.add_argument(
            "--skip-size-check",
            action="store_true",
            help="Пропустить проверку размера файлов",
        )

    def handle(self, *args, **options):
        """Основной метод выполнения команды."""
        dry_run = options.get("dry_run", False)
        verbose = options.get("verbose", False)
        prefer_new_path = options.get("prefer_new_path", False)
        min_size_kb = options.get("min_size", DEFAULT_MIN_SIZE_KB)
        skip_size_check = options.get("skip_size_check", False)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'=' * 60}\n"
                f"  Дедупликация изображений в базе данных\n"
                f"{'=' * 60}\n"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 Режим DRY-RUN: изменения НЕ будут сохранены\n")
            )

        if not skip_size_check:
            self.stdout.write(
                f"📏 Минимальный размер файла: {min_size_kb}KB\n"
            )

        # Обработка Product.base_images
        products_result = self._deduplicate_products(
            dry_run, verbose, prefer_new_path, min_size_kb, skip_size_check
        )

        # Обработка ProductVariant.gallery_images
        variants_result = self._deduplicate_variants(
            dry_run, verbose, prefer_new_path, min_size_kb, skip_size_check
        )

        # Итоговая статистика
        self._print_summary(products_result, variants_result, dry_run)

    def _get_file_size_kb(self, image_path: str) -> float | None:
        """
        Получить размер файла в KB.
        
        Args:
            image_path: Относительный путь к файлу в MEDIA_ROOT
            
        Returns:
            Размер в KB или None если файл не найден
        """
        try:
            if default_storage.exists(image_path):
                size_bytes = default_storage.size(image_path)
                return size_bytes / 1024
            return None
        except Exception as e:
            logger.debug(f"Error getting file size for {image_path}: {e}")
            return None

    def _deduplicate_products(
        self, 
        dry_run: bool, 
        verbose: bool, 
        prefer_new_path: bool,
        min_size_kb: int,
        skip_size_check: bool,
    ) -> dict:
        """
        Дедупликация Product.base_images.

        Returns:
            Dict со статистикой
        """
        self.stdout.write("\n📦 Обработка Product.base_images...")

        products = Product.objects.exclude(base_images__isnull=True).exclude(
            base_images=[]
        )
        total = products.count()

        if total == 0:
            self.stdout.write("   Нет товаров с изображениями")
            return {"total": 0, "with_duplicates": 0, "removed": 0, "small_removed": 0}

        with_duplicates = 0
        total_removed = 0
        small_removed = 0

        with tqdm(
            total=total,
            desc="   Товары",
            unit="шт",
            disable=not self.stdout.isatty(),
        ) as pbar:
            for product in products.iterator(chunk_size=100):
                original_images = product.base_images or []
                
                # Шаг 1: Фильтрация по размеру
                filtered_images = original_images
                small_files = []
                
                if not skip_size_check:
                    filtered_images = []
                    for img_path in original_images:
                        size_kb = self._get_file_size_kb(img_path)
                        if size_kb is not None and size_kb < min_size_kb:
                            small_files.append((img_path, size_kb))
                        else:
                            filtered_images.append(img_path)
                    
                    # Если после фильтрации не осталось изображений,
                    # оставляем первое (даже маленькое)
                    if len(filtered_images) == 0 and len(original_images) > 0:
                        # Возвращаем первое изображение
                        filtered_images = [original_images[0]]
                        # Убираем его из списка мелких
                        small_files = [
                            (p, s) for p, s in small_files 
                            if p != original_images[0]
                        ]
                    
                    small_removed += len(small_files)
                
                # Шаг 2: Дедупликация
                deduplicated = self._deduplicate_list(
                    filtered_images, prefer_new_path
                )

                removed_count = len(original_images) - len(deduplicated)

                if removed_count > 0:
                    with_duplicates += 1
                    total_removed += removed_count

                    if verbose:
                        self.stdout.write(
                            f"\n   [{product.onec_id}] {product.name}:"
                        )
                        self.stdout.write(f"      Было: {len(original_images)}")
                        self.stdout.write(f"      Стало: {len(deduplicated)}")
                        self.stdout.write(f"      Удалено: {removed_count}")

                        # Показать удалённые мелкие файлы
                        for img_path, size_kb in small_files:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"      ❌ {img_path} ({size_kb:.1f}KB < {min_size_kb}KB)"
                                )
                            )

                        # Показать удалённые дубли
                        kept_set = set(deduplicated)
                        removed_as_dups = [
                            img for img in filtered_images if img not in kept_set
                        ]
                        for img in removed_as_dups:
                            self.stdout.write(
                                self.style.WARNING(f"      - {img} (дубликат)")
                            )

                    if not dry_run:
                        product.base_images = deduplicated
                        product.save(update_fields=["base_images"])

                pbar.update(1)

        return {
            "total": total,
            "with_duplicates": with_duplicates,
            "removed": total_removed,
            "small_removed": small_removed,
        }

    def _deduplicate_variants(
        self, 
        dry_run: bool, 
        verbose: bool, 
        prefer_new_path: bool,
        min_size_kb: int,
        skip_size_check: bool,
    ) -> dict:
        """
        Дедупликация ProductVariant.gallery_images.

        Returns:
            Dict со статистикой
        """
        self.stdout.write("\n🎨 Обработка ProductVariant.gallery_images...")

        variants = ProductVariant.objects.exclude(
            gallery_images__isnull=True
        ).exclude(gallery_images=[])
        total = variants.count()

        if total == 0:
            self.stdout.write("   Нет вариантов с галереей изображений")
            return {"total": 0, "with_duplicates": 0, "removed": 0, "small_removed": 0}

        with_duplicates = 0
        total_removed = 0
        small_removed = 0

        with tqdm(
            total=total,
            desc="   Варианты",
            unit="шт",
            disable=not self.stdout.isatty(),
        ) as pbar:
            for variant in variants.iterator(chunk_size=100):
                original_images = variant.gallery_images or []
                
                # Шаг 1: Фильтрация по размеру
                filtered_images = original_images
                small_files = []
                
                if not skip_size_check:
                    filtered_images = []
                    for img_path in original_images:
                        size_kb = self._get_file_size_kb(img_path)
                        if size_kb is not None and size_kb < min_size_kb:
                            small_files.append((img_path, size_kb))
                        else:
                            filtered_images.append(img_path)
                    
                    # Если после фильтрации не осталось изображений,
                    # оставляем первое (даже маленькое)
                    if len(filtered_images) == 0 and len(original_images) > 0:
                        # Возвращаем первое изображение
                        filtered_images = [original_images[0]]
                        # Убираем его из списка мелких
                        small_files = [
                            (p, s) for p, s in small_files 
                            if p != original_images[0]
                        ]
                    
                    small_removed += len(small_files)
                
                # Учитываем main_image при дедупликации
                main_image = variant.main_image
                seen_filenames = set()
                
                if main_image:
                    # main_image может быть ImageFieldFile, преобразуем в строку
                    main_image_str = str(main_image) if main_image else ""
                    if main_image_str:
                        main_filename = Path(main_image_str).name
                        if main_filename:
                            seen_filenames.add(main_filename)
                
                deduplicated = self._deduplicate_list(
                    filtered_images, prefer_new_path, seen_filenames
                )

                removed_count = len(original_images) - len(deduplicated)

                if removed_count > 0:
                    with_duplicates += 1
                    total_removed += removed_count

                    if verbose:
                        self.stdout.write(
                            f"\n   [{variant.onec_id}] SKU: {variant.sku}:"
                        )
                        self.stdout.write(f"      Было: {len(original_images)}")
                        self.stdout.write(f"      Стало: {len(deduplicated)}")
                        self.stdout.write(f"      Удалено: {removed_count}")

                        # Показать удалённые мелкие файлы
                        for img_path, size_kb in small_files:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"      ❌ {img_path} ({size_kb:.1f}KB < {min_size_kb}KB)"
                                )
                            )

                    if not dry_run:
                        variant.gallery_images = deduplicated
                        variant.save(update_fields=["gallery_images"])

                pbar.update(1)

        return {
            "total": total,
            "with_duplicates": with_duplicates,
            "removed": total_removed,
            "small_removed": small_removed,
        }

    def _deduplicate_list(
        self,
        image_paths: list[str],
        prefer_new_path: bool = False,
        initial_seen: set[str] | None = None,
    ) -> list[str]:
        """
        Удаление дублей из списка путей по filename.

        Args:
            image_paths: Список путей к изображениям
            prefer_new_path: Если True, предпочитать пути без 'import_files/'
            initial_seen: Начальный набор уже виденных filename'ов

        Returns:
            Дедуплицированный список
        """
        seen_filenames: set[str] = set(initial_seen) if initial_seen else set()
        result: list[str] = []
        
        # Группируем по filename
        by_filename: dict[str, list[str]] = {}
        for path in image_paths:
            filename = Path(path).name if path else ""
            if filename:
                if filename not in by_filename:
                    by_filename[filename] = []
                by_filename[filename].append(path)
        
        # Выбираем один путь для каждого filename
        for filename, paths in by_filename.items():
            if filename in seen_filenames:
                continue
                
            if len(paths) == 1:
                result.append(paths[0])
            else:
                # Есть дубли - выбираем один
                if prefer_new_path:
                    # Предпочитаем путь БЕЗ import_files/
                    chosen = None
                    for p in paths:
                        if "import_files" not in p:
                            chosen = p
                            break
                    if chosen is None:
                        chosen = paths[0]
                else:
                    # По умолчанию берём первый
                    chosen = paths[0]
                
                result.append(chosen)
            
            seen_filenames.add(filename)
        
        return result

    def _print_summary(
        self, products_result: dict, variants_result: dict, dry_run: bool
    ):
        """Вывод итоговой статистики."""
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'=' * 60}\n"
                f"  {'✅ Дедупликация завершена' if not dry_run else '🔍 DRY-RUN завершён'}\n"
                f"{'=' * 60}\n"
            )
        )

        self.stdout.write("📊 Статистика Product.base_images:")
        self.stdout.write(f"   • Всего товаров с изображениями: {products_result['total']}")
        self.stdout.write(f"   • Товаров с дублями/мелкими: {products_result['with_duplicates']}")
        self.stdout.write(
            self.style.SUCCESS(
                f"   • Удалено записей: {products_result['removed']}"
            )
            if products_result["removed"] > 0
            else f"   • Удалено записей: 0"
        )
        if products_result.get("small_removed", 0) > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"   • Из них мелких файлов: {products_result['small_removed']}"
                )
            )

        self.stdout.write("\n📊 Статистика ProductVariant.gallery_images:")
        self.stdout.write(f"   • Всего вариантов с галереей: {variants_result['total']}")
        self.stdout.write(f"   • Вариантов с дублями/мелкими: {variants_result['with_duplicates']}")
        self.stdout.write(
            self.style.SUCCESS(
                f"   • Удалено записей: {variants_result['removed']}"
            )
            if variants_result["removed"] > 0
            else f"   • Удалено записей: 0"
        )
        if variants_result.get("small_removed", 0) > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"   • Из них мелких файлов: {variants_result['small_removed']}"
                )
            )

        total_removed = products_result["removed"] + variants_result["removed"]
        total_small = products_result.get("small_removed", 0) + variants_result.get("small_removed", 0)
        
        self.stdout.write(
            self.style.SUCCESS(f"\n🎯 Всего удалено записей: {total_removed}")
        )
        if total_small > 0:
            self.stdout.write(
                self.style.ERROR(f"   Из них мелких файлов (<100KB): {total_small}")
            )

        if dry_run and total_removed > 0:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  Это был тестовый запуск. "
                    "Запустите без --dry-run для сохранения изменений."
                )
            )

        self.stdout.write("")
