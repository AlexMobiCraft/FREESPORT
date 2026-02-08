import re
import os

def fix_order_status_import():
    path = 'tests/unit/test_order_status_import.py'
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    # Pattern to match: indentation, code, two spaces, # [AI-Review]...
    # Example: "        mock_order.pk = 123  # [AI-Review][Medium] Data Integrity: pk должен соответствовать order_id=order-123"
    pattern = re.compile(r'^(\s+)(.*\.pk = \d+)(\s{2})# (\[AI-Review\].*)$')

    for line in lines:
        match = pattern.match(line.rstrip('\n'))
        if match:
            indent, code, space, comment = match.groups()
            # Move comment to previous line
            new_lines.append(f'{indent}# {comment}\n')
            new_lines.append(f'{indent}{code}\n')
        else:
            new_lines.append(line)

    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Processed {path}")

def fix_order_export_service():
    path = 'tests/unit/test_order_export_service.py'
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    target_line_part = "# With prefetch, we expect: 1 for orders + 1 for items + 1 for variants + 1 for users = ~4 queries"
    
    for line in lines:
        if target_line_part in line:
            indent = line[:line.find('#')]
            new_lines.append(f'{indent}# With prefetch, we expect:\n')
            new_lines.append(f'{indent}# 1 for orders + 1 for items + 1 for variants + 1 for users = ~4 queries\n')
        else:
            new_lines.append(line)

    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Processed {path}")

if __name__ == "__main__":
    fix_order_status_import()
    fix_order_export_service()
