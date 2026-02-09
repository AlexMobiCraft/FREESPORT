import os


def fix_order_export_service():
    path = "tests/unit/test_order_export_service.py"
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if "# 1 for orders + 1 for items + 1 for variants + 1 for users = ~4 queries" in line:
            indent = line[: line.find("#")]
            new_lines.append(f"{indent}# 1 for orders + 1 for items + 1 for variants + 1 for users\n")
            new_lines.append(f"{indent}# = ~4 queries\n")
        else:
            new_lines.append(line)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Processed {path}")


def fix_order_status_import():
    path = "tests/unit/test_order_status_import.py"
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        # Fix long comments with [AI-Review]
        if stripped.startswith("# [AI-Review]") and len(line) > 88:
            indent = line[: line.find("#")]
            comment_content = stripped[2:].strip()  # remove '# '

            # Split logic
            if "Data Integrity: pk должен соответствовать" in comment_content:
                parts = comment_content.split("Data Integrity: ")
                new_lines.append(f"{indent}# {parts[0]}Data Integrity:\n")
                new_lines.append(f"{indent}# {parts[1]}\n")
            elif "Data Integrity: order_id должен соответствовать" in comment_content:
                parts = comment_content.split("Data Integrity: ")
                new_lines.append(f"{indent}# {parts[0]}Data Integrity:\n")
                new_lines.append(f"{indent}# {parts[1]}\n")
            elif "Data Integrity: sent_to_1c_at устанавливается при" in comment_content:
                new_lines.append(f"{indent}# [AI-Review][Medium] Data Integrity:\n")
                new_lines.append(f"{indent}# sent_to_1c_at устанавливается при sent_to_1c=True.\n")
            elif "Cache Key Collision Risk: num: префикс" in comment_content:
                new_lines.append(f"{indent}# [AI-Review][High] Cache Key Collision Risk:\n")
                new_lines.append(f"{indent}# num: префикс предотвращает коллизии.\n")
            elif "_bulk_fetch_orders создаёт ключи" in comment_content:
                new_lines.append(f"{indent}# [AI-Review][High] _bulk_fetch_orders создаёт ключи\n")
                new_lines.append(f"{indent}# с правильными префиксами.\n")
            elif "Race Condition Risk: select_for_update()" in comment_content:
                new_lines.append(f"{indent}# [AI-Review][Medium] Race Condition Risk:\n")
                new_lines.append(f"{indent}# select_for_update() в fallback запросе.\n")
            elif "Logic/Data Consistency: дата сбрасывается" in comment_content:
                new_lines.append(f"{indent}# [AI-Review][Medium] Logic/Data Consistency:\n")
                new_lines.append(f"{indent}# дата сбрасывается при пустом теге.\n")
            elif "Logic/Data Consistency: дата НЕ меняется" in comment_content:
                new_lines.append(f"{indent}# [AI-Review][Medium] Logic/Data Consistency:\n")
                new_lines.append(f"{indent}# дата НЕ меняется если тега нет.\n")
            elif "Logic/Data Consistency: OrderUpdateData имеет флаги" in comment_content:
                new_lines.append(f"{indent}# [AI-Review][Medium] Logic/Data Consistency:\n")
                new_lines.append(f"{indent}# OrderUpdateData имеет флаги *_present.\n")
            elif "Переходы между финальными статусами блокируются" in comment_content:
                new_lines.append(f"{indent}# [AI-Review][Medium] Переходы между финальными\n")
                new_lines.append(f"{indent}# статусами блокируются.\n")
            elif "Обновление статуса логируется на DEBUG" in comment_content:
                new_lines.append(f"{indent}# [AI-Review][Medium] Обновление статуса логируется\n")
                new_lines.append(f"{indent}# на DEBUG, не INFO.\n")
            elif "Logic/Data Consistency: _parse_document устанавливает" in comment_content:
                new_lines.append(f"{indent}# [AI-Review][Medium] Logic/Data Consistency:\n")
                new_lines.append(f"{indent}# _parse_document устанавливает флаги.\n")
            else:
                # Default split
                mid = len(comment_content) // 2
                split_idx = comment_content.rfind(" ", 0, mid + 10)
                if split_idx == -1:
                    split_idx = mid
                new_lines.append(f"{indent}# {comment_content[:split_idx]}\n")
                new_lines.append(f"{indent}# {comment_content[split_idx + 1:]}\n")
        else:
            new_lines.append(line)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Processed {path}")


if __name__ == "__main__":
    fix_order_export_service()
    fix_order_status_import()
