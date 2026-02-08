
import os

file_path = 'backend/apps/products/services/variant_import.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the corrupted section
start_line = -1
for i, line in enumerate(lines):
    if 'def _log_error(self, message: str, data: Any) -> None:' in line:
        start_line = i
        break

if start_line != -1:
    # Look for where _log_error ends (it has 3 lines of body)
    # def _log_error(self, message: str, data: Any) -> None:
    #     """Логирование ошибки"""
    #     logger.error(f"{message}: {data}")
    #     self.stats["errors"] += 1
    
    # Check if lines match expectation
    if 'self.stats["errors"] += 1' in lines[start_line + 3]:
        # The corruption starts after this line
        corruption_start = start_line + 4
        
        # We want to replace everything from here until 'def process_price_types' or the end of the corrupted block
        # The corrupted block seems to be:
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
        
        # We will insert the correct get_stats method
        
        correct_method = [
            '\n',
            '    def get_stats(self) -> dict[str, Any]:\n',
            '        """Возвращает статистику импорта"""\n',
            '        # Limit the lists to avoid huge JSONs\n',
            '        limit = 100\n',
            '        stats: dict[str, Any] = self.stats.copy()\n',
            '\n',
            '        stats["updated_products_ids"] = self.updated_products[:limit]\n',
            '        stats["updated_variants_ids"] = self.updated_variants[:limit]\n',
            '\n',
            '        if len(self.updated_products) > limit:\n',
            '            stats["updated_products_ids"].append(\n',
            '                f"...and {len(self.updated_products) - limit} more"\n',
            '            )\n',
            '\n',
            '        if len(self.updated_variants) > limit:\n',
            '            stats["updated_variants_ids"].append(\n',
            '                f"...and {len(self.updated_variants) - limit} more"\n',
            '            )\n',
            '\n',
            '        return stats\n'
        ]
        
        # Find where to stop replacing. We look for the next method or end of file.
        # But we know the corruption is specific.
        # The corrupted lines are indented with 12 spaces in some places?
        # Let's just find the next method definition
        
        end_replacement = -1
        for j in range(corruption_start, len(lines)):
            if 'def process_price_types' in lines[j] or '# =====================' in lines[j]:
                end_replacement = j
                break
        
        if end_replacement != -1:
            # Replace
            new_lines = lines[:corruption_start] + correct_method + lines[end_replacement:]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print("Successfully fixed variant_import.py")
        else:
            print("Could not find end of corrupted block")
    else:
        print("_log_error body does not match expectation")
else:
    print("_log_error not found")
