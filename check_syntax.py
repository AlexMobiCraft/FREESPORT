
import ast
import sys

filename = 'backend/tests/unit/test_order_status_import.py'

try:
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    ast.parse(source, filename=filename)
    print("Syntax OK")
except SyntaxError as e:
    print(f"SyntaxError: {e}")
    print(f"Line: {e.lineno}, Offset: {e.offset}")
    print(f"Text: {e.text}")
    if e.lineno:
        lines = source.splitlines()
        start = max(0, e.lineno - 5)
        end = min(len(lines), e.lineno + 5)
        for i in range(start, end):
            prefix = ">> " if i + 1 == e.lineno else "   "
            print(f"{prefix}{i+1}: {lines[i]}")
except Exception as e:
    print(f"Error: {e}")
