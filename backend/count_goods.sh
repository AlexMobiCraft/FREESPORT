#!/bin/bash
# Подсчет товаров в XML файлах

echo "Подсчет товаров в goods/*.xml:"
for file in /app/data/import_1c/goods/*.xml; do
    count=$(grep -c "<Товар>" "$file" 2>/dev/null || echo "0")
    echo "  $(basename $file): $count товаров"
done

echo ""
echo "Общее количество:"
grep -h "<Товар>" /app/data/import_1c/goods/*.xml 2>/dev/null | wc -l
