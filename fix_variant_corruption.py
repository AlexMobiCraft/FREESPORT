
import os

file_path = 'backend/apps/products/services/variant_import.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We are looking for the corrupted _log_error and missing get_stats
# Pattern:
#     def _log_error(self, message: str, data: Any) -> None:
#         """Логирование ошибки"""
#         logger.error(f"{message}: {data}")
#         self.stats["errors"] += 1
#             stats["updated_products_ids"].append(
#                 f"...and {len(self.updated_products) - limit} more"
#             )

# We want to replace it with:
#     def _log_error(self, message: str, data: Any) -> None:
#         """Логирование ошибки"""
#         logger.error(f"{message}: {data}")
#         self.stats["errors"] += 1
#
#     def get_stats(self) -> dict[str, Any]:
#         """Возвращает статистику импорта"""
#         # Limit the lists to avoid huge JSONs
#         limit = 100
#         stats: dict[str, Any] = self.stats.copy()
#
#         stats["updated_products_ids"] = self.updated_products[:limit]
#         stats["updated_variants_ids"] = self.updated_variants[:limit]
#
#         if len(self.updated_products) > limit:
#             stats["updated_products_ids"].append(
#                 f"...and {len(self.updated_products) - limit} more"
#             )
#
#         if len(self.updated_variants) > limit:
#             stats["updated_variants_ids"].append(
#                 f"...and {len(self.updated_variants) - limit} more"
#             )
#
#         return stats

new_lines = []
skip = False
for i, line in enumerate(lines):
    if skip:
        if 'def process_price_types' in line:
            skip = False
            new_lines.append(line)
        continue

    if 'def _log_error(self, message: str, data: Any) -> None:' in line:
        # Add _log_error and get_stats correctly
        new_lines.append('    def _log_error(self, message: str, data: Any) -> None:\n')
        new_lines.append('        """Логирование ошибки"""\n')
        new_lines.append('        logger.error(f"{message}: {data}")\n')
        new_lines.append('        self.stats["errors"] += 1\n')
        new_lines.append('\n')
        new_lines.append('    def get_stats(self) -> dict[str, Any]:\n')
        new_lines.append('        """Возвращает статистику импорта"""\n')
        new_lines.append('        # Limit the lists to avoid huge JSONs\n')
        new_lines.append('        limit = 100\n')
        new_lines.append('        stats: dict[str, Any] = self.stats.copy()\n')
        new_lines.append('\n')
        new_lines.append('        stats["updated_products_ids"] = self.updated_products[:limit]\n')
        new_lines.append('        stats["updated_variants_ids"] = self.updated_variants[:limit]\n')
        new_lines.append('\n')
        new_lines.append('        if len(self.updated_products) > limit:\n')
        new_lines.append('            stats["updated_products_ids"].append(\n')
        new_lines.append('                f"...and {len(self.updated_products) - limit} more"\n')
        new_lines.append('            )\n')
        new_lines.append('\n')
        new_lines.append('        if len(self.updated_variants) > limit:\n')
        new_lines.append('            stats["updated_variants_ids"].append(\n')
        new_lines.append('                f"...and {len(self.updated_variants) - limit} more"\n')
        new_lines.append('            )\n')
        new_lines.append('\n')
        new_lines.append('        return stats\n')
        new_lines.append('\n')
        
        # Skip the corrupted lines in original file until next method
        # We assume the corruption goes until process_price_types
        # We need to find where to resume.
        # But wait, my logic above "if skip: ... continue" handles resuming.
        # So I just need to enable skip mode.
        skip = True
        
        # However, I need to be careful not to skip the lines I just processed if I'm not careful.
        # The loop is iterating over `lines`.
        # I added the replacement. Now I set skip=True.
        # The next iterations will skip until process_price_types is found.
        # But I need to make sure I don't miss process_price_types line itself.
        # In the "if skip" block, I check for it.
        
        # Also need to consume the body of _log_error from original file if it was there?
        # The original file has _log_error header, then body.
        # I replaced header and body.
        # So I should skip the body in original file too.
        # The corruption starts inside _log_error body in the original file (line 1352).
        
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed variant_import.py corruption.")
