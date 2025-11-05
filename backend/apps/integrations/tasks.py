"""
Celery задачи для асинхронного импорта данных из 1С
"""
import logging
from pathlib import Path
from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.management import call_command

from apps.products.models import ImportSession

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.integrations.tasks.run_selective_import_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def run_selective_import_task(
    self, selected_types: list[str], data_dir: str | None = None
) -> dict[str, Any]:
    """
    Асинхронная задача для выборочного импорта данных из 1С.

    Args:
        selected_types: Список типов импорта (catalog, stocks, prices, customers)
        data_dir: Директория с данными 1С (если None, берется из settings)

    Returns:
        Dict с результатами импорта

    Raises:
        Exception: При критических ошибках импорта
    """
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Запуск выборочного импорта: {selected_types}")

    # Получаем директорию с данными
    if data_dir is None:
        data_dir = getattr(settings, "ONEC_DATA_DIR", None)
        if not data_dir:
            error_msg = "Настройка ONEC_DATA_DIR не найдена в settings"
            logger.error(f"[Task {task_id}] {error_msg}")
            raise ValueError(error_msg)

    results: list[dict[str, str]] = []
    import_order = ["catalog", "stocks", "prices", "customers"]

    try:
        for import_type in import_order:
            if import_type not in selected_types:
                continue

            logger.info(f"[Task {task_id}] Начало импорта: {import_type}")

            try:
                result = _execute_import_type(import_type, data_dir, task_id)
                results.append(result)
                logger.info(
                    f"[Task {task_id}] Импорт {import_type} завершен: {result['message']}"
                )
            except Exception as e:
                error_msg = f"Ошибка импорта {import_type}: {e}"
                logger.error(f"[Task {task_id}] {error_msg}", exc_info=True)
                # При ошибке прерываем цепочку
                raise Exception(error_msg) from e

        # Формируем итоговый результат
        summary = {
            "status": "success",
            "task_id": task_id,
            "completed_imports": [r["type"] for r in results],
            "messages": [r["message"] for r in results],
        }
        logger.info(f"[Task {task_id}] Импорт завершен успешно: {summary}")
        return summary

    except Exception as e:
        logger.error(
            f"[Task {task_id}] Критическая ошибка импорта: {e}",
            exc_info=True,
        )
        # Повторная попытка при ошибке (до max_retries раз)
        raise self.retry(exc=e)


def _execute_import_type(
    import_type: str, data_dir: str, task_id: str
) -> dict[str, str]:
    """
    Выполнение импорта конкретного типа данных.

    Args:
        import_type: Тип импорта (catalog, stocks, prices, customers)
        data_dir: Директория с данными 1С
        task_id: ID задачи Celery для логирования

    Returns:
        Dict с результатом импорта

    Raises:
        FileNotFoundError: Если файл не найден
        Exception: При ошибках выполнения команды
    """
    data_path = Path(data_dir)

    if import_type == "catalog":
        # Для каталога проверяем директорию
        if not data_path.exists():
            raise FileNotFoundError(f"Директория данных не найдена: {data_dir}")

        logger.info(f"[Task {task_id}] Запуск import_catalog_from_1c --file-type=all")
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(data_dir),
            "--file-type",
            "all",
        )
        return {"type": "catalog", "message": "Каталог импортирован"}

    elif import_type == "stocks":
        # Проверяем наличие директории с остатками
        rests_dir = data_path / "rests"
        if not rests_dir.exists():
            raise FileNotFoundError(
                f"Директория остатков не найдена: {rests_dir}. "
                f"Убедитесь, что данные из 1С выгружены в {data_dir}"
            )

        logger.info(f"[Task {task_id}] Запуск import_catalog_from_1c --file-type=rests")
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(data_dir),
            "--file-type",
            "rests",
        )
        return {"type": "stocks", "message": "Остатки обновлены"}

    elif import_type == "prices":
        if not data_path.exists():
            raise FileNotFoundError(f"Директория данных не найдена: {data_dir}")

        logger.info(
            f"[Task {task_id}] Запуск import_catalog_from_1c --file-type=prices"
        )
        call_command(
            "import_catalog_from_1c",
            "--data-dir",
            str(data_dir),
            "--file-type",
            "prices",
        )
        return {"type": "prices", "message": "Цены обновлены"}

    elif import_type == "customers":
        # Ищем любой файл contragents в директории
        contragents_dir = data_path / "contragents"
        if not contragents_dir.exists():
            raise FileNotFoundError(
                f"Директория контрагентов не найдена: {contragents_dir}"
            )

        # Ищем первый XML файл с контрагентами
        contragents_files = list(contragents_dir.glob("contragents*.xml"))
        if not contragents_files:
            raise FileNotFoundError(
                f"Файлы контрагентов не найдены в {contragents_dir}. "
                f"Убедитесь, что данные из 1С выгружены."
            )

        # Используем первый найденный файл
        file_path = contragents_files[0]
        logger.info(f"[Task {task_id}] Запуск import_customers_from_1c")
        call_command("import_customers_from_1c", "--file", str(file_path))
        return {"type": "customers", "message": "Клиенты импортированы"}

    else:
        raise ValueError(f"Неизвестный тип импорта: {import_type}")
