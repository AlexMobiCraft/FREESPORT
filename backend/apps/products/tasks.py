import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, Retry, SoftTimeLimitExceeded
from django.conf import settings
from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.utils import timezone

from apps.integrations.onec_exchange.file_service import FileStreamService
from apps.integrations.onec_exchange.file_type_detection import detect_file_type
from apps.integrations.onec_exchange.routing_service import get_import_base, is_session_import_dir
from apps.products.models import ImportSession

logger = logging.getLogger("import_tasks")

IMPORT_LOCK_KEY_PREFIX = "onec:import:lock:"

# Типы, которые команда `import_products_from_1c` действительно собирает.
# `contragents` — маршрут на отдельную команду, `all` — «имя ни о чём не
# говорит»; ни то, ни другое обещанием конкретного файла быть не может.
_CATALOG_TYPES = frozenset({"goods", "offers", "prices", "rests"})

# Пометка прогона, которому 1С не обещала имён и в чьём каталоге обмена нет
# своих XML. Текст стабилен: на подстроку вешается приёмочный тест, и менять
# его нельзя без правки теста.
SESSION_HAS_NO_OWN_FILES = "В каталоге обмена этой сессии нет своих XML-файлов"

# Порог автоматической уборки осиротевших каталогов обмена. Зафиксирован
# контрактом стори `onec-exchange-dir-isolation` (AC5), а не «на усмотрение».
STALE_EXCHANGE_DIR_HOURS = 24


def _import_lock_key(data_dir: str) -> str:
    """Ключ лока каталога обмена. Лок именно на каталог, а не на сессию.

    После изоляции `data_dir` у каждой сессии свой, и ключ от него дал бы
    каждой задаче собственный лок: сериализация задач исчезла бы целиком и
    молча, вопреки Non-goal спеки «не устранять само ожидание лока». Поэтому
    для сессионной раскладки ключ считается от ОБЩЕГО корня обмена. Ручной
    прогон (`ONEC_DATA_DIR`) и тесты с `tmp_path` ключуются по себе, как раньше.
    """
    key_source = str(get_import_base()) if is_session_import_dir(data_dir) else data_dir
    return f"{IMPORT_LOCK_KEY_PREFIX}{key_source}"


def _release_import_lock(lock_key: str, lock_token: str) -> None:
    """Снять лок каталога обмена, но только если владелец — эта задача.

    Сверка значения нужна, чтобы задача, пережившая истечение TTL, не сняла
    лок, который к тому моменту успел перезахватить сосед. Гонка «прочитали
    своё значение → TTL истёк → сосед захватил → удалили чужой лок» остаётся
    теоретически возможной, но требует импорта дольше ONEC_IMPORT_LOCK_TTL
    (по умолчанию 1800 с). При таком запасе это принимаемый риск.
    """
    try:
        if cache.get(lock_key) == lock_token:
            cache.delete(lock_key)
    except Exception as exc:  # pragma: no cover - падение Redis не должно валить импорт
        logger.warning(f"Failed to release import lock {lock_key}: {exc}")


def _mark_session_failed(session_id: int, message: str) -> None:
    """Пометить сессию как FAILED, дописав причину в отчёт."""
    try:
        session = ImportSession.objects.get(pk=session_id)
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        session.status = ImportSession.ImportStatus.FAILED
        session.error_message = message
        session.report += f"[{timestamp}] {message}\n"
        session.save(update_fields=["status", "error_message", "report", "updated_at"])
    except Exception as exc:  # pragma: no cover - диагностика, не влияет на результат
        logger.critical(f"Failed to mark session {session_id} as failed: {exc}")


@shared_task(name="apps.products.tasks.process_1c_import_task", bind=True)
def process_1c_import_task(
    self: Any,
    session_id: int,
    data_dir: str | None = None,
    zip_filename: str | None = None,
    source_filename: str | list[str] | None = None,
) -> str:
    """
    Задача для асинхронного запуска импорта из 1С.

    Args:
        session_id: ID сессии ImportSession
        data_dir: Путь к директории с файлами (опционально)
        zip_filename: Имя ZIP-архива для асинхронной распаковки
        source_filename: Имя файла, присланного 1С (`rests_1_16_….xml`), либо
            список имён. Определяет шаг импорта. Список приходит от архива:
            имя `.zip` плюс XML, распакованный из него обработчиком
            `mode=import` (к старту задачи архива на диске уже нет).
            Отдельный параметр, а не `zip_filename`: последний включает ветку
            распаковки архива.

    Returns:
        Результат выполнения ('success' или 'failure')
    """
    # Story 3.2: Defered Unpacking
    # Files (including ZIPs) are already moved to import_dir by the view (handle_complete).
    # We need to find them there and unpack.
    target_import_dir = Path(data_dir) if data_dir else Path(str(settings.ONEC_EXCHANGE["IMPORT_DIR"]))
    # Story 36.1: единый резолвленный путь для management-команд. Без него
    # вызов задачи без data_dir уводил импорт товаров на ONEC_DATA_DIR
    # (ручные выгрузки data/import_1c/), хотя ZIP и контрагенты в этой же
    # задаче уже читаются из приватного ONEC_EXCHANGE["IMPORT_DIR"].
    effective_data_dir = data_dir or str(target_import_dir)

    # Лок каталога обмена: 1С отдаёт сегмент каждые ~6,5 с при обработке 7-8 с,
    # а воркер prefork держит nproc процессов — без сериализации соседние задачи
    # чистят файлы друг друга. cache.add на Redis — атомарный SETNX.
    #
    # Захват и retry живут ВНЕ внешнего try/except: celery.exceptions.Retry
    # наследует Exception, и обработчик ниже пометил бы сессию FAILED.
    lock_key = _import_lock_key(effective_data_dir)
    lock_token = self.request.id or f"session-{session_id}"

    try:
        lock_acquired = cache.add(lock_key, lock_token, settings.ONEC_IMPORT_LOCK_TTL)
    except Exception as exc:
        # Redis лёг: взять лок нечем, а импортировать без него — вернуть ту самую
        # гонку. Падаем закрыто, но сессия обязана это показать: без пометки она
        # висела бы IN_PROGRESS до `cleanup_stale_import_sessions` (порог 2 часа),
        # хотя отказ публикации `retry` ниже сессию уже переводит в FAILED.
        logger.error(f"Failed to acquire import lock for session {session_id}: {exc}")
        _mark_session_failed(
            session_id,
            f"Не удалось взять лок каталога обмена {effective_data_dir} — импорт не запущен: {exc}",
        )
        return "failure"

    if not lock_acquired:
        try:
            holder = cache.get(lock_key)
        except Exception:  # pragma: no cover - только для текста лога
            holder = "unknown"
        logger.info(
            f"Import directory {effective_data_dir} is locked by {holder}; "
            f"retrying session {session_id} (attempt {self.request.retries + 1})"
        )
        # Отчёт засоряется только один раз за задачу, а не на каждой попытке.
        if self.request.retries == 0:
            try:
                ImportSession.objects.filter(pk=session_id).update(
                    report=Concat(
                        F("report"),
                        Value(
                            f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                            f"Каталог обмена занят другим импортом, задача отложена.\n"
                        ),
                    ),
                    updated_at=timezone.now(),
                )
            except Exception as exc:  # pragma: no cover - диагностика
                logger.warning(f"Failed to log lock wait for session {session_id}: {exc}")

        try:
            raise self.retry(
                countdown=settings.ONEC_IMPORT_LOCK_RETRY_COUNTDOWN,
                max_retries=settings.ONEC_IMPORT_LOCK_MAX_RETRIES,
            )
        except Retry:
            # Штатный путь: задача вернулась в брокер, сессия остаётся IN_PROGRESS.
            raise
        except MaxRetriesExceededError:
            _mark_session_failed(
                session_id,
                f"Каталог обмена {effective_data_dir} оставался занят дольше допустимого "
                f"({settings.ONEC_IMPORT_LOCK_MAX_RETRIES} попыток × "
                f"{settings.ONEC_IMPORT_LOCK_RETRY_COUNTDOWN} с) — импорт не запущен.",
            )
            return "failure"
        except Exception as exc:
            # Переотправка не доехала до брокера (Redis недоступен, kombu
            # OperationalError). Без этой ветки сессия осталась бы IN_PROGRESS
            # навсегда — до порога `cleanup_stale_import_sessions` в 2 часа.
            logger.error(f"Failed to reschedule session {session_id} after busy lock: {exc}")
            _mark_session_failed(
                session_id,
                f"Каталог обмена {effective_data_dir} занят, а переотправить задачу не удалось: {exc}",
            )
            return "failure"

    try:
        session = ImportSession.objects.get(pk=session_id)
        session.status = ImportSession.ImportStatus.IN_PROGRESS
        session.celery_task_id = self.request.id

        # Обновляем отчет о начале
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        session.report += f"[{timestamp}] Задача Celery запущена. Начинаем импорт...\n"
        session.save(update_fields=["status", "celery_task_id", "report", "updated_at"])

        # Story 3.1: Асинхронная распаковка архива (если передан)
        if zip_filename and zip_filename.lower().endswith(".zip") and data_dir:
            try:
                # Extract sessid from data_dir path (data_dir = .../1c_import/<sessid>)
                sessid = Path(data_dir).name
                file_service = FileStreamService(sessid)
                import_dir_path = Path(data_dir)

                file_service.unpack_zip(zip_filename, import_dir_path)

                timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                session.report += f"[{timestamp}] Архив {zip_filename} успешно распакован.\n"
                session.save(update_fields=["report"])
            except Exception as e:
                timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                session.status = ImportSession.ImportStatus.FAILED
                session.error_message = f"Ошибка распаковки архива: {e}"
                session.report += f"[{timestamp}] ОШИБКА РАСПАКОВКИ: {e}\n"
                session.save(update_fields=["status", "error_message", "report"])
                logger.error(f"Unpack failed for session {session_id}: {e}")
                return "failure"

        # XML, который эта задача сама достала из архивов. Архив, распакованный
        # здесь, тут же удаляется — значит его содержимое принадлежит этому
        # прогону, и именно оно (а не файлы, лежавшие в общем каталоге до нас)
        # становится обещанием. См. `promised_filenames` ниже.
        unpacked_xml_names: list[str] = []

        if target_import_dir.exists():
            zip_files = list(target_import_dir.glob("*.zip"))
            if zip_files:
                logger.info(f"Found {len(zip_files)} ZIP files in import dir. Unpacking...")
                import zipfile

                from apps.integrations.onec_exchange.routing_service import (
                    XML_ROUTING_RULES,
                    image_relative_name,
                    images_dir_for,
                )

                for zf in zip_files:
                    try:
                        # Direct unpacking to target directory
                        with zipfile.ZipFile(zf, "r") as zip_ref:
                            zip_ref.extractall(target_import_dir)
                            unpacked_files = zip_ref.namelist()

                        logger.info(f"Unpacked: {zf.name} to {target_import_dir}")

                        # Route unpacked files to subdirectories
                        routed_count = 0
                        for filename in unpacked_files:
                            file_path = target_import_dir / filename
                            if not file_path.exists() or not file_path.is_file():
                                continue

                            # Logic similar to FileRoutingService.route_file
                            name_lower = filename.lower()
                            suffix = file_path.suffix.lower()
                            dest_path = None

                            if suffix == ".xml":
                                # Sort rules by length of prefix descending to match most specific first
                                # e.g. 'propertiesOffers' (len 16) before 'properties' (len 10)
                                sorted_rules = sorted(
                                    XML_ROUTING_RULES.items(),
                                    key=lambda x: len(x[0]),
                                    reverse=True,
                                )
                                for prefix, subdir in sorted_rules:
                                    if name_lower.startswith(prefix):
                                        dest_path = target_import_dir / subdir.rstrip("/") / filename
                                        break
                            elif suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                                # Картинки — в ОБЩИЙ каталог мимо сессионного.
                                # Это вторая, дублирующая копия маршрутизации
                                # распакованного (первая — в
                                # `ImportOrchestratorService._route_unpacked_files`):
                                # архивы, накопившиеся в каталоге, распаковывает
                                # сама задача при `mode=complete`. Правится
                                # только вместе с первой, иначе картинки
                                # разъедутся мимо общего каталога.
                                dest_path = images_dir_for(target_import_dir) / image_relative_name(filename)

                            if dest_path is not None:
                                # Имя внутри архива может нести свой каталог
                                # (`import_files/photo.jpg`) — без создания
                                # родителя move падал, и картинка оставалась
                                # в корне каталога обмена, где её не ищет
                                # ни один шаг импорта.
                                dest_path.parent.mkdir(parents=True, exist_ok=True)

                                try:
                                    # Move file
                                    import shutil

                                    shutil.move(str(file_path), str(dest_path))
                                    routed_count += 1
                                    if suffix == ".xml":
                                        unpacked_xml_names.append(dest_path.name)
                                except Exception as move_err:
                                    logger.warning(f"Failed to route {filename}: {move_err}")

                        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                        session.report += (
                            f"[{timestamp}] Архив {zf.name} распакован ({len(unpacked_files)} файлов). "
                            f"Распределено по папкам: {routed_count}.\n"
                        )

                        # Delete the ZIP file after unpacking
                        try:
                            zf.unlink()
                            logger.info(f"Deleted archive: {zf.name}")
                        except OSError as e:
                            logger.warning(f"Failed to delete archive {zf.name}: {e}")

                    except Exception as e:
                        logger.error(f"Failed to unpack {zf.name}: {e}")
                        session.report += f"[{timezone.now()}] Ошибка распаковки {zf.name}: {e}\n"
                        # Remove the corrupted zip file so it doesn't get retried endlessly
                        try:
                            zf.unlink()
                            logger.info(f"Deleted corrupted archive: {zf.name}")
                        except OSError as del_err:
                            logger.warning(f"Failed to delete corrupted archive {zf.name}: {del_err}")

                session.save(update_fields=["report"])

        # Story 3.2: Defensive directory creation
        # Ensure import directory and all required subdirectories exist
        # to satisfy management command validation.
        if data_dir:
            import_path = Path(data_dir)
            if not import_path.exists():
                logger.warning(f"Import directory {data_dir} missing. Creating it.")
                import_path.mkdir(parents=True, exist_ok=True)

            # Create required subdirectories if they don't exist
            # This prevents "Missing mandatory subdirectory" errors in 'all' mode
            required_subdirs = ["goods", "offers", "prices", "rests", "priceLists"]
            for subdir in required_subdirs:
                subdir_path = import_path / subdir
                if not subdir_path.exists():
                    subdir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created missing subdirectory: {subdir}")

            # Debug: Log directory structure
            try:
                files = list(import_path.rglob("*"))
                logger.info(f"Import directory ready: {data_dir} ({len(files)} items found)")
            except Exception as e:
                logger.warning(f"Failed to list directory contents: {e}")

        # Determine file type based on the name 1C sent.
        # This prevents running unnecessary steps and allows 1C to trigger
        # granular imports (e.g. only stocks or only prices).
        # Что этот прогон обязан прочитать. Имя файла — обещание только тогда,
        # когда команда импорта такой файл вообще собирает.
        #
        # Имя архива обещанием быть не может: `detect_file_type("import_files.zip")`
        # даёт `goods`, но XML с таким именем команда не найдёт никогда. Раньше
        # это означало «обещания нет» — и задача архива уходила в несужаемый
        # импорт, забирая backlog соседних `goods*.xml` из общего каталога.
        # Теперь связь архива с сегментами явная: обещание архива — XML, который
        # он принёс. Распаковать архив мог как обработчик `mode=import` (тогда
        # имена приходят списком в `source_filename`), так и сама задача
        # (`mode=complete`, накопившиеся в каталоге zip) — тогда их даёт
        # `unpacked_xml_names`.
        if isinstance(source_filename, (list, tuple)):
            source_names = [str(name) for name in source_filename if name]
        elif source_filename:
            source_names = [str(source_filename)]
        else:
            source_names = []

        archive_names = [name for name in source_names if name.lower().endswith(".zip")]
        xml_names = [name for name in source_names if name.lower().endswith(".xml")]
        if archive_names:
            xml_names += unpacked_xml_names

        promised_filenames: list[str] | None
        skip_catalog_import = False
        promised = sorted({name for name in xml_names if detect_file_type(name) in _CATALOG_TYPES})

        if promised:
            types = {detect_file_type(name) for name in promised}
            detected_file_type = types.pop() if len(types) == 1 else "all"
            promised_filenames = promised
        elif any(detect_file_type(name) == "contragents" for name in xml_names):
            detected_file_type = "contragents"
            promised_filenames = None
        elif archive_names:
            # Архив без своих XML: собственного сегмента у него нет, а сгребать
            # чужие — та самая потеря данных. Изображения остаются в
            # goods/import_files и достанутся задаче своего goods-сегмента;
            # cleanup команды при этом не выполняется.
            detected_file_type = detect_file_type(archive_names[0])
            skip_catalog_import = True
            promised_filenames = None
        else:
            detected_file_type = detect_file_type((source_names[0] if source_names else None) or zip_filename)
            promised_filenames = None

        # Определяем тип импорта: контрагенты или товарный каталог.
        #
        # Наличие `contragents*.xml` в общем каталоге само по себе НЕ означает,
        # что импортировать надо контрагентов: файл мог остаться от соседней
        # сессии. Если 1С обещала этому прогону конкретный товарный сегмент
        # (`rests_1_12_….xml`), маршрут определяет имя файла — иначе сегмент
        # молча съедался чужим импортом контрагентов, а сессия отчитывалась
        # успехом. По каталогу решаем только там, где имени не обещали:
        # `mode=complete` и ручной прогон.
        contragents_dir = target_import_dir / "contragents" if target_import_dir.exists() else None
        has_contragents = bool(
            contragents_dir and contragents_dir.exists() and list(contragents_dir.glob("contragents*.xml"))
        )
        import_customers = detected_file_type == "contragents" or (
            detected_file_type == "all" and has_contragents and not promised_filenames
        )

        # Прогон без обещания сгребает каталог целиком — и потому не имеет права
        # работать, пока живы другие сессии. Их файлы уже обещаны собственным
        # задачам, которые стоят в очереди за локом.
        #
        # Прод-прогон AC9 2026-08-27: 223 сессии, 53 `failed`, и 48 из 48
        # объяснённых падений имели потребителем именно `mode=complete`. 1С шлёт
        # `mode=import` на каждый файл и `mode=complete` следом, каждые пару
        # секунд; сегмент уходил в очередь («Каталог обмена занят»), подоспевший
        # `complete` забирал его вместе со всем каталогом и удалял, а задача
        # сегмента, получив лок, падала «не найден в каталоге обмена». Данные
        # доезжали, но выгрузка отчитывалась провалом.
        #
        # Это тот же guard, что уже стоит на post-import cleanup ниже и в
        # `views.handle_init`. Файлы без хозяина по-прежнему забирает `complete`:
        # при отсутствии других активных сессий сбор идёт как раньше.
        defer_to_active_sessions = False
        if not promised_filenames and not import_customers and not skip_catalog_import:
            defer_to_active_sessions = (
                ImportSession.objects.filter(status=ImportSession.ImportStatus.IN_PROGRESS)
                .exclude(pk=session.pk)
                .exists()
            )

        # Прогон без обещанных имён при сессионной раскладке видит только свой
        # каталог. Если своих XML в нём нет — импортировать нечего, и молчать об
        # этом нельзя: тихий COMPLETED неотличим от «данные доехали».
        # `defer_to_active_sessions` остаётся страховкой для ручных прогонов по
        # общему каталогу и потому проверяется первым.
        session_dir_has_no_own_files = (
            not promised_filenames
            and not import_customers
            and not skip_catalog_import
            and not defer_to_active_sessions
            and is_session_import_dir(effective_data_dir)
            and not any(target_import_dir.rglob("*.xml"))
        )

        if import_customers:
            logger.info(
                f"Starting 1C customers import for session {session_id} "
                f"(key={session.session_key}, data_dir={effective_data_dir})"
            )
            call_command("import_customers_from_1c", data_dir=effective_data_dir)
        elif defer_to_active_sessions:
            message = (
                "Импорт каталога пропущен: в работе другие сессии обмена, и файлы "
                "в каталоге обещаны их задачам. Несужаемый сбор забрал бы чужие "
                "сегменты и утопил их сессии в FAILED."
            )
            logger.info(f"Session {session_id}: {message}")
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            session.report += f"[{timestamp}] {message}\n"
            session.save(update_fields=["report", "updated_at"])
        elif session_dir_has_no_own_files:
            message = (
                f"{SESSION_HAS_NO_OWN_FILES}: импорт каталога пропущен. "
                f"Файлы соседних сессий этому прогону не принадлежат и не читаются."
            )
            logger.info(f"Session {session_id}: {message}")
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            session.report += f"[{timestamp}] {message}\n"
            session.save(update_fields=["report", "updated_at"])
        elif skip_catalog_import:
            message = (
                f"Архив {archive_names[0]} не принёс ни одного XML-сегмента "
                f"(только изображения либо он уже распакован соседней задачей). "
                f"Файлы оставлены в каталоге обмена, импорт каталога не запускается: "
                f"чужие сегменты этому прогону не принадлежат."
            )
            logger.info(f"Session {session_id}: {message}")
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            session.report += f"[{timestamp}] {message}\n"
            session.save(update_fields=["report", "updated_at"])
        else:
            # Запуск management команды импорта товарного каталога
            args: list[Any] = []
            options = {
                "celery_task_id": self.request.id,
                "file_type": detected_file_type,
                "import_session_id": session_id,
                "data_dir": effective_data_dir,
                # Имена передаются только когда 1С обещала конкретные XML.
                # Тогда команда обязана их прочитать, иначе сессия FAILED:
                # тихий успех с нулём записей — это и есть потеря данных.
                # Для "all" (mode=complete, ручной прогон) обещания нет.
                # У архива обещание — XML, который распаковала эта же задача.
                "source_filename": promised_filenames,
            }

            logger.info(
                f"Starting 1C import for session {session_id} "
                f"(key={session.session_key}, file_type={detected_file_type}, "
                f"file={', '.join(source_names) or zip_filename})"
            )
            call_command("import_products_from_1c", *args, **options)

        # Финализация сессии (если команда сама не завершила её)
        session.refresh_from_db()
        if session.status != ImportSession.ImportStatus.COMPLETED:
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            session.status = ImportSession.ImportStatus.COMPLETED
            session.finished_at = timezone.now()
            session.report += f"[{timestamp}] Импорт успешно завершен.\n"
            session.save(update_fields=["status", "finished_at", "report", "updated_at"])

        # Уборка каталога обмена СВОЕЙ сессии. Guard `other_active` сохранён
        # (Non-goal спеки): он всё ещё нужен ручным прогонам по общему каталогу,
        # где `data_dir` у всех один. После изоляции область уборки сузилась до
        # собственной папки, а сама папка следом удаляется — иначе каталоги
        # копятся навсегда (на проде накопилось 32 276 штук).
        try:
            other_active = (
                ImportSession.objects.filter(
                    status=ImportSession.ImportStatus.IN_PROGRESS,
                )
                .exclude(pk=session.pk)
                .exists()
            )

            if other_active:
                logger.info("Skipping import directory cleanup — other sessions are still IN_PROGRESS.")
            elif session.session_key:
                from apps.integrations.onec_exchange.routing_service import FileRoutingService

                routing_service = FileRoutingService(str(session.session_key))
                cleaned = routing_service.cleanup_import_dir()
                logger.info(f"Post-import cleanup removed {cleaned} items from import directory.")
                if is_session_import_dir(routing_service.import_dir):
                    removed_dirs = routing_service.remove_session_dirs()
                    logger.info(f"Post-import cleanup removed {removed_dirs} session directories.")
            else:
                logger.warning("Session key is missing, skipping cleanup.")
        except Exception as cleanup_err:
            logger.warning(f"Failed post-import cleanup: {cleanup_err}")

        return "success"

    except ImportSession.DoesNotExist:
        logger.error(f"ImportSession {session_id} not found")
        return "failure"
    except Exception as e:
        logger.error(f"Error in process_1c_import_task: {e}")
        try:
            session = ImportSession.objects.get(pk=session_id)
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

            if isinstance(e, CommandError):
                error_prefix = "ОШИБКА КОМАНДЫ"
                status = ImportSession.ImportStatus.FAILED
                msg = str(e)
            elif isinstance(e, SoftTimeLimitExceeded):
                error_prefix = "ПРЕВЫШЕН ЛИМИТ ВРЕМЕНИ"
                status = ImportSession.ImportStatus.FAILED
                msg = "Time limit exceeded"
            else:
                error_prefix = "КРИТИЧЕСКАЯ ОШИБКА"
                status = ImportSession.ImportStatus.FAILED
                msg = str(e)

            # Update session if not already handled by command
            if session.status != ImportSession.ImportStatus.FAILED:
                session.status = status
                session.error_message = msg

            session.report += f"[{timestamp}] {error_prefix}: {msg}\n"
            session.save(update_fields=["status", "error_message", "report", "updated_at"])
        except Exception as db_err:
            logger.critical(f"Failed to update session status after error: {db_err}")

        return "failure"

    finally:
        _release_import_lock(lock_key, lock_token)


@shared_task(name="apps.products.tasks.cleanup_stale_import_sessions")
def cleanup_stale_import_sessions() -> int:
    """
    Задача для очистки "зависших" сессий импорта.
    Находит сессии со статусом 'in_progress', которые не обновлялись более 2 часов.
    """
    stale_threshold = timezone.now() - timedelta(hours=2)

    stale_sessions = ImportSession.objects.filter(
        status=ImportSession.ImportStatus.IN_PROGRESS, updated_at__lt=stale_threshold
    )

    count = stale_sessions.count()
    if count > 0:
        logger.info(f"Cleaning up {count} stale import sessions")
        for session in stale_sessions:
            session.status = ImportSession.ImportStatus.FAILED
            session.error_message = "Зависла/Таймаут (не обновлялась более 2 часов)"
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            session.report += f"[{timestamp}] Сессия помечена как зависшая инструментом очистки.\n"
            session.save(update_fields=["status", "error_message", "report", "updated_at"])

    return count


@shared_task(name="apps.products.tasks.cleanup_stale_exchange_dirs")
def cleanup_stale_exchange_dirs(max_age_hours: int = STALE_EXCHANGE_DIR_HOURS) -> int:
    """Убрать осиротевшие каталоги обмена 1С старше порога.

    После изоляции каждая сессия получает собственный каталог в `1c_temp` и
    `1c_import`. Штатно он удаляется по завершении обмена, но воркер может
    упасть до уборки — тогда каталог остаётся навсегда (на проде так накопилось
    32 276 папок). Порог — `STALE_EXCHANGE_DIR_HOURS`, зафиксирован контрактом.

    Заодно подрезаются старые файлы общего каталога картинок: он единственный,
    что остаётся общим, и после изоляции его не чистит ни одна сессия.

    Возраст считается по самому каталогу сессии, а не по файлам внутри: задача
    на каждом прогоне создаёт в нём подпапки `goods`/`offers`/…, поэтому пустым
    он не бывает и `rmdir` тут не годится — только `shutil.rmtree`.
    """
    import shutil
    import time

    from apps.integrations.onec_exchange.routing_service import (
        IMAGES_SUBDIR,
        SHARED_ROOT_NAMES,
        get_import_base,
        get_temp_base,
    )

    threshold = time.time() - max_age_hours * 3600
    removed = 0

    for root in (get_import_base(), get_temp_base()):
        if not root.exists():
            continue
        for item in root.iterdir():
            # Общий каталог картинок, легаси-раскладка типов и флаг `.dry_run`
            # каталогами сессий не являются: снести их — потерять картинки,
            # которые ещё нужны XML других сессий.
            if item.name in SHARED_ROOT_NAMES or not item.is_dir():
                continue
            try:
                if item.stat().st_mtime >= threshold:
                    continue
                shutil.rmtree(item)
                removed += 1
                logger.info(f"Removed stale exchange dir: {item}")
            except OSError as exc:
                logger.warning(f"Failed to remove stale exchange dir {item}: {exc}")

    shared_images = get_import_base() / IMAGES_SUBDIR
    if shared_images.exists():
        for image in shared_images.rglob("*"):
            if not image.is_file():
                continue
            try:
                if image.stat().st_mtime >= threshold:
                    continue
                image.unlink()
                removed += 1
            except OSError as exc:
                logger.warning(f"Failed to remove stale exchange image {image}: {exc}")

    if removed:
        logger.info(f"Stale exchange cleanup removed {removed} items (threshold {max_age_hours}h)")

    return removed
