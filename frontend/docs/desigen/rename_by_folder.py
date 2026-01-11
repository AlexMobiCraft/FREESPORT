import os
import sys
import shutil  # <-- Добавлен импорт для копирования


def rename_files_in_subfolders():
    """
    Главная функция для поиска подпапок в текущей директории,
    переименования файлов внутри них и копирования в общую папку.
    """

    # Получаем текущую директорию, где запущен скрипт
    current_dir = os.getcwd()

    # +++ Создаем общую директорию для скопированных файлов +++
    common_dest_dir = os.path.join(current_dir, "_ALL_RENAMED_FILES_")
    try:
        os.makedirs(common_dest_dir, exist_ok=True)
        print(f"--- Файлы будут скопированы в: {common_dest_dir} ---")
    except OSError as e:
        print(
            f"[!] КРИТИЧЕСКАЯ ОШИБКА: Не удалось создать директорию {common_dest_dir}. {e}"
        )
        print("--- Работа скрипта прекращена. ---")
        return  # Выходим, если не можем создать главную папку
    # +++ Конец добавления +++

    # Получаем имя самого скрипта, чтобы случайно не переименовать его
    try:
        # __file__ работает, когда скрипт запускается как файл
        script_name = os.path.basename(__file__)
    except NameError:
        # Это сработает, если код запускается в интерактивной среде или как строка
        # (например, в некоторых IDE)
        try:
            script_name = os.path.basename(sys.argv[0])
        except (IndexError, AttributeError):
            # Резервный вариант, если не удается определить имя скрипта
            script_name = "rename_by_folder.py"

    print(f"--- Запуск в директории: {current_dir} ---")
    print(f"--- Имя скрипта (будет пропущено): {script_name} ---")

    # 1. Перебираем все элементы в текущей директории
    for item_name in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item_name)

        # 2. Проверяем, является ли элемент директорией (подпапкой)
        if os.path.isdir(item_path):
            # +++ Пропускаем нашу новую общую папку, чтобы не обрабатывать ее +++
            if item_name == "_ALL_RENAMED_FILES_":
                print("\n[*] Пропускаем общую директорию (_ALL_RENAMED_FILES_)...")
                continue
            # +++ Конец добавления +++

            subdir_name = item_name
            subdir_path = item_path
            print(f"\n[+] Обработка подпапки: {subdir_name}")

            # 3. Инициализируем счетчик для файлов внутри этой подпапки
            file_counter = 1

            # 4. Получаем список файлов в подпапке и сортируем для предсказуемого порядка
            try:
                # Фильтруем, чтобы случайно не захватить сам скрипт, если он там
                files_in_subdir = sorted(
                    f for f in os.listdir(subdir_path) if f != script_name
                )
            except PermissionError:
                print(f"  [!] Ошибка: нет доступа к {subdir_path}. Пропускаем.")
                continue

            # 5. Перебираем все отфильтрованные файлы внутри подпапки
            for file_name in files_in_subdir:
                old_file_path = os.path.join(subdir_path, file_name)

                # 6. Убеждаемся, что это файл, а не под-под-папка
                if os.path.isfile(old_file_path):
                    # 7. Получаем расширение файла
                    # os.path.splitext('file.txt') -> ('file', '.txt')
                    # os.path.splitext('.gitignore') -> ('.gitignore', '') - это проблема

                    base_name, extension = os.path.splitext(file_name)

                    # Если у файла нет расширения (например, '.gitignore'),
                    # os.path.splitext вернет ('', '.gitignore') или ('.gitignore', '')
                    # Нам нужно это обработать.
                    if not extension and base_name.startswith("."):
                        # Это файл типа .gitignore, у него нет "расширения"
                        extension = ""  # Оставляем без расширения
                    elif not extension and not base_name.startswith("."):
                        # Это файл типа 'README'
                        extension = ""  # Оставляем без расширения

                    # 8. Создаем новое имя.
                    # Мы будем добавлять счетчик, чтобы избежать конфликтов,
                    # так как в папке может быть много файлов.
                    new_file_name = f"{subdir_name}_{file_counter}{extension}"
                    new_file_path = os.path.join(subdir_path, new_file_name)

                    # 9. Проверяем, не существует ли уже файл с таким именем
                    # (на случай, если файл 'папка_1.txt' уже был создан)
                    while os.path.exists(new_file_path):
                        file_counter += 1
                        new_file_name = f"{subdir_name}_{file_counter}{extension}"
                        new_file_path = os.path.join(subdir_path, new_file_name)

                    # 10. Переименовываем файл
                    try:
                        os.rename(old_file_path, new_file_path)
                        print(f"  -> Переименовано: {file_name}  ->  {new_file_name}")

                        # +++ Добавляем КОПИРОВАНИЕ в общую папку +++
                        try:
                            # Источник - только что переименованный файл
                            # Назначение - наша общая папка + новое имя файла
                            destination_copy_path = os.path.join(
                                common_dest_dir, new_file_name
                            )
                            # copy2 также копирует метаданные (например, дату создания)
                            shutil.copy2(new_file_path, destination_copy_path)
                            print(f"    -> Скопировано в: {common_dest_dir}")
                        except shutil.Error as e_copy:
                            print(
                                f"    [!] Ошибка копирования {new_file_name}: {e_copy}"
                            )
                        # +++ Конец добавления +++

                        file_counter += 1  # Увеличиваем счетчик для СЛЕДУЮЩЕГО файла
                    except OSError as e:
                        print(f"  [!] Ошибка при переименовании {file_name}: {e}")

    print("\n--- Готово! Все подпапки обработаны. ---")


if __name__ == "__main__":
    rename_files_in_subfolders()
