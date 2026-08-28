"""Изоляция каталога обмена 1С по сессии (стори `onec-exchange-dir-isolation`).

Каталог обмена был общий для всех сессий: 1С шлёт `mode=import` на каждый файл и
`mode=complete` следом, задачи сериализуются локом каталога, и прогон без
обещанного имени (`mode=complete`) успевал собрать по маске чужой свежий файл,
прочитать его и законно удалить как обработанный. Сегмент, отстоявший очередь за
локом, обещанного файла не находил и падал в FAILED.

Замер прода 28.08.2026, окно 7 дней: 110 упавших сессий, 85 из них с «файл не
найден в каталоге обмена», и все 85 — ровно те, что ждали лока.

`session_key` уникален для каждого файла (1С не держит cookie-сессию между
запросами), поэтому каталог на сессию = каталог на файл: пересечься физически
невозможно.

XML берутся из закоммиченного среза реальной выгрузки 1С
(`backend/tests/fixtures/1c-data/`) — синтетику проект запрещает.
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from django.core.cache import cache
from django.core.management import call_command

from apps.integrations.onec_exchange.file_service import FileStreamService
from apps.integrations.onec_exchange.routing_service import FileRoutingService
from apps.products.management.commands.import_products_from_1c import Command
from apps.products.models import ImportSession, Product
from apps.products.tasks import (
    SESSION_HAS_NO_OWN_FILES,
    _import_lock_key,
    cleanup_stale_exchange_dirs,
    process_1c_import_task,
)

ONEC_FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "1c-data"

# Восемь реальных сегментов остатков с исходными именами 1С (`rests_1_<N>_<guid>.xml`).
# Порядок — числовой по номеру сегмента, а не лексикографический.
REAL_SEGMENTS = sorted(
    (ONEC_FIXTURES / "rests" / "segments").glob("rests_1_*.xml"),
    key=lambda p: int(p.name.split("_")[2]),
)

# Реальная выгрузка товаров вместе с настоящими картинками: пути внутри XML
# имеют вид `import_files/<xx>/<file>.jpg`.
GOODS_SOURCE_DIR = ONEC_FIXTURES / "goods" / "import_files"
GOODS_XML = GOODS_SOURCE_DIR / "goods.xml"
# Товар из этой выгрузки, у которого есть <Картинка> в каталоге `01/`.
GOODS_PRODUCT_WITH_IMAGES = "018d777d-9094-11ec-a2ff-04421a23d8e8"


def _segment_path(index: int) -> Path:
    """Реальный сегмент остатков по порядковому номеру (1-based)."""
    return REAL_SEGMENTS[index - 1]


def _segment_name(index: int) -> str:
    """Имя сегмента ровно в том виде, в котором его присылает 1С."""
    return _segment_path(index).name


@pytest.fixture
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def exchange(tmp_path, settings):
    """Приватные каталоги обмена 1С, переведённые в tmp_path.

    Оба каталога подменяются целиком: изоляция считает сессионным ровно тот
    каталог, чей родитель — `ONEC_EXCHANGE["IMPORT_DIR"]`, и без подмены правило
    смотрело бы на боевой путь.
    """
    temp_dir = tmp_path / "1c_temp"
    import_dir = tmp_path / "1c_import"
    temp_dir.mkdir()
    import_dir.mkdir()
    settings.ONEC_EXCHANGE = {
        **settings.ONEC_EXCHANGE,
        "TEMP_DIR": temp_dir,
        "IMPORT_DIR": import_dir,
    }
    return SimpleNamespace(temp=temp_dir, imports=import_dir)


def _upload(sessid: str, source: Path, filename: str | None = None) -> Path:
    """Провести файл штатным путём 1С: temp сессии → каталог обмена.

    Именно так файл попадает в каталог на проде (`handle_file_upload` +
    `_transfer_files`), поэтому тест не выкладывает файлы руками.
    """
    name = filename or source.name
    stream = FileStreamService(sessid)
    stream._ensure_session_dir()
    shutil.copyfile(source, stream.get_file_path(name))
    return FileRoutingService(sessid).move_to_import(name)


def _session(sessid: str, status: str) -> ImportSession:
    return ImportSession.objects.create(session_key=sessid, status=status)


def _import_dir(sessid: str) -> Path:
    return FileRoutingService(sessid).import_dir


def _run_task(session: ImportSession, sessid: str, source_filename: str | None, task_id: str) -> str:
    """Прогон задачи импорта по каталогу своей сессии."""
    return process_1c_import_task.apply(
        args=(session.pk,),
        kwargs={"data_dir": str(_import_dir(sessid)), "source_filename": source_filename},
        task_id=task_id,
    ).get()


@pytest.mark.django_db
class TestSessionDirIsolation:
    """AC1 — сессионная раскладка каталога обмена."""

    def test_import_dir_is_session_scoped(self, exchange):
        """Каталог обмена сессии — подкаталог общего корня с именем сессии."""
        router = FileRoutingService("sess-a")

        assert router.import_dir == exchange.imports / "sess-a"
        assert FileRoutingService("sess-b").import_dir != router.import_dir

    def test_uploaded_segment_lands_in_own_dir(self, exchange):
        """Файл сессии виден только в её каталоге."""
        target = _upload("sess-a", _segment_path(1))

        assert target == exchange.imports / "sess-a" / "rests" / _segment_name(1)
        assert not (exchange.imports / "sess-b" / "rests" / _segment_name(1)).exists()

    def test_neighbour_segment_survives_promiseless_run(self, exchange, clean_cache):
        """Ядро дефекта: прогон без обещания не имеет права съесть чужой сегмент.

        Воспроизводится прод-механика сессий 66453/66454: сессия A (`mode=complete`)
        держит лок и работает, файл сессии B уже лежит в каталоге обмена (окно
        между `_transfer_files` и `_dispatch_import`, где B ещё PENDING), поэтому
        guard `defer_to_active_sessions` его не видит. На общем каталоге A
        собирает файл B по маске, читает и удаляет — B, дождавшись лока, падает.
        """
        session_a = _session("sess-a", ImportSession.ImportStatus.PENDING)
        session_b = _session("sess-b", ImportSession.ImportStatus.PENDING)

        own = _upload("sess-a", _segment_path(1))
        neighbour = _upload("sess-b", _segment_path(2))

        # `mode=complete` идёт с file_type=all — бэкап БД к изоляции отношения не имеет.
        with patch.object(Command, "_backup_before_import"):
            assert _run_task(session_a, "sess-a", "complete", "task-iso-a") == "success"

        assert not own.exists(), "Свой сегмент прогон обязан прочитать и убрать"
        assert neighbour.exists(), "Чужой сегмент прогон без обещания читать не вправе"

        # Очередь за локом отстояла — теперь работает B со своим обещанным файлом.
        session_b.status = ImportSession.ImportStatus.IN_PROGRESS
        session_b.save(update_fields=["status"])
        assert _run_task(session_b, "sess-b", _segment_name(2), "task-iso-b") == "success"

        session_a.refresh_from_db()
        session_b.refresh_from_db()
        assert session_a.status == ImportSession.ImportStatus.COMPLETED
        assert session_b.status == ImportSession.ImportStatus.COMPLETED
        assert not neighbour.exists(), "Свой сегмент сессия B обязана прочитать сама"

    def test_session_id_must_be_single_path_segment(self, exchange):
        """`sessid` приходит из query-параметра и становится сегментом пути под rmtree."""
        for evil in ("../escape", "a/b", "a\\b", "..", ""):
            with pytest.raises(ValueError):
                FileRoutingService(evil)


@pytest.mark.django_db
class TestSharedImages:
    """AC2 — картинки остаются общими и доступны XML любой сессии."""

    def test_images_are_routed_to_shared_dir(self, exchange):
        """Картинка ложится в общий `import_files`, а не в каталог своей сессии."""
        image = next((GOODS_SOURCE_DIR / "01").glob("*.jpg"))
        target = _upload("sess-images", image)

        assert target == exchange.imports / "import_files" / image.name
        assert not (exchange.imports / "sess-images" / "import_files").exists()

    def test_xml_from_session_dir_resolves_shared_images(self, exchange, tmp_path, settings):
        """goods.xml изолированной сессии находит картинки чужого обмена."""
        settings.MEDIA_ROOT = str(tmp_path / "media")

        data_dir = _import_dir("sess-goods")
        (data_dir / "goods").mkdir(parents=True)
        shutil.copyfile(GOODS_XML, data_dir / "goods" / "goods.xml")

        # Картинки приехали отдельным обменом с другим sessid — они в общем каталоге.
        shared_images = exchange.imports / "import_files"
        for sub in ("01", "03", "06"):
            shutil.copytree(GOODS_SOURCE_DIR / sub, shared_images / sub)

        session = _session("sess-goods", ImportSession.ImportStatus.IN_PROGRESS)
        call_command(
            "import_products_from_1c",
            data_dir=str(data_dir),
            file_type="goods",
            import_session_id=session.pk,
        )

        product = Product.objects.get(onec_id=GOODS_PRODUCT_WITH_IMAGES)
        assert product.base_images, "Картинки из общего каталога обязаны разрешиться"
        assert shared_images.exists(), "Общий каталог картинок чистит не сессия"

    def test_legacy_image_layout_still_resolves(self, exchange, tmp_path, settings):
        """Переходное окно выката: картинки лежат в старой раскладке `goods/import_files`.

        Частичное разрешение картинок обрезало бы состав фото товара
        (`_import_base_images(mirror_composition=True)`), поэтому фолбэк на
        легаси-раскладку обязателен, пока прод не перешёл на новую.
        """
        settings.MEDIA_ROOT = str(tmp_path / "media")

        data_dir = _import_dir("sess-legacy")
        (data_dir / "goods").mkdir(parents=True)
        shutil.copyfile(GOODS_XML, data_dir / "goods" / "goods.xml")

        legacy_images = exchange.imports / "goods" / "import_files"
        for sub in ("01", "03", "06"):
            shutil.copytree(GOODS_SOURCE_DIR / sub, legacy_images / sub)

        session = _session("sess-legacy", ImportSession.ImportStatus.IN_PROGRESS)
        call_command(
            "import_products_from_1c",
            data_dir=str(data_dir),
            file_type="goods",
            import_session_id=session.pk,
        )

        product = Product.objects.get(onec_id=GOODS_PRODUCT_WITH_IMAGES)
        assert product.base_images, "Легаси-раскладка картинок обязана разрешаться фолбэком"


@pytest.mark.django_db
class TestPromiselessRunKeepsHandsOff:
    """AC3 — `mode=complete` не сгребает каталог."""

    def test_complete_without_own_files_completes_with_note(self, exchange, clean_cache):
        """Своих файлов нет: COMPLETED с пометкой, соседи целы и не прочитаны."""
        session_a = _session("sess-empty", ImportSession.ImportStatus.PENDING)
        _session("sess-owner", ImportSession.ImportStatus.PENDING)

        neighbours = [_upload("sess-owner", _segment_path(i)) for i in (3, 4)]

        with patch.object(Command, "_backup_before_import"):
            assert _run_task(session_a, "sess-empty", "complete", "task-empty") == "success"

        session_a.refresh_from_db()
        assert session_a.status == ImportSession.ImportStatus.COMPLETED
        assert SESSION_HAS_NO_OWN_FILES in session_a.report
        assert all(path.exists() for path in neighbours), "Файлы соседей обязаны остаться на диске"

    def test_complete_with_own_files_still_imports(self, exchange, clean_cache):
        """Свои файлы есть — прогон работает как раньше."""
        session = _session("sess-own", ImportSession.ImportStatus.PENDING)
        own = _upload("sess-own", _segment_path(5))

        with patch.object(Command, "_backup_before_import"):
            assert _run_task(session, "sess-own", "complete", "task-own") == "success"

        session.refresh_from_db()
        assert session.status == ImportSession.ImportStatus.COMPLETED
        assert SESSION_HAS_NO_OWN_FILES not in session.report
        assert not own.exists(), "Свой сегмент прогон обязан прочитать"


@pytest.mark.django_db
class TestCleanupStaysInOwnDir:
    """AC4 — уборка ограничена каталогом своей сессии."""

    def test_cleanup_does_not_touch_neighbour(self, exchange):
        own = _upload("sess-a", _segment_path(1))
        neighbour = _upload("sess-b", _segment_path(2))

        deleted = FileRoutingService("sess-a").cleanup_import_dir()

        assert deleted >= 1
        assert not own.exists()
        assert neighbour.exists(), "Каталог соседней сессии уборке не подлежит"

    def test_force_cleanup_does_not_touch_shared_images(self, exchange):
        image = next((GOODS_SOURCE_DIR / "01").glob("*.jpg"))
        shared = _upload("sess-a", image)
        _upload("sess-a", _segment_path(1))

        FileRoutingService("sess-a").cleanup_import_dir(force=True)

        assert shared.exists(), "Общие картинки нужны XML соседних сессий"

    def test_remove_session_dirs_clears_both_roots(self, exchange):
        _upload("sess-a", _segment_path(1))
        router = FileRoutingService("sess-a")

        router.cleanup_import_dir()
        router.remove_session_dirs()

        assert not (exchange.imports / "sess-a").exists()
        assert not (exchange.temp / "sess-a").exists()


@pytest.mark.django_db
class TestStaleExchangeDirCleanup:
    """AC5 — каталоги обмена не накапливаются."""

    @staticmethod
    def _age(path: Path, hours: float) -> None:
        old = time.time() - hours * 3600
        os.utime(path, (old, old))

    def test_stale_dirs_removed_fresh_kept(self, exchange):
        _upload("sess-old", _segment_path(1))
        _upload("sess-new", _segment_path(2))
        self._age(exchange.imports / "sess-old", 25)
        self._age(exchange.temp / "sess-old", 25)

        removed = cleanup_stale_exchange_dirs()

        assert removed >= 2
        assert not (exchange.imports / "sess-old").exists()
        assert not (exchange.temp / "sess-old").exists()
        assert (exchange.imports / "sess-new").exists()

    def test_threshold_is_24_hours(self, exchange):
        """Порог зафиксирован контрактом: 23 часа — ещё свежий каталог."""
        _upload("sess-young", _segment_path(1))
        self._age(exchange.imports / "sess-young", 23)
        self._age(exchange.temp / "sess-young", 23)

        assert cleanup_stale_exchange_dirs() == 0
        assert (exchange.imports / "sess-young").exists()

    def test_shared_dirs_are_protected(self, exchange):
        """Общий каталог картинок и легаси-раскладка каталогами сессий не являются."""
        image = next((GOODS_SOURCE_DIR / "01").glob("*.jpg"))
        shared = _upload("sess-a", image)
        legacy = exchange.imports / "goods" / "import_files"
        legacy.mkdir(parents=True)
        (legacy / "keep.jpg").write_bytes(b"legacy")
        self._age(exchange.imports / "import_files", 48)
        self._age(exchange.imports / "goods", 48)

        cleanup_stale_exchange_dirs()

        assert shared.exists(), "Каталог общих картинок сносить нельзя"
        assert (legacy / "keep.jpg").exists(), "Легаси-раскладка нужна фолбэку картинок"

    def test_stale_shared_images_are_pruned(self, exchange):
        """Общий каталог картинок больше никто не чистит — он не вправе расти вечно."""
        image = next((GOODS_SOURCE_DIR / "01").glob("*.jpg"))
        old_image = _upload("sess-a", image)
        fresh_image = _upload("sess-b", next((GOODS_SOURCE_DIR / "03").glob("*.jpg")))
        self._age(old_image, 25)

        cleanup_stale_exchange_dirs()

        assert not old_image.exists()
        assert fresh_image.exists()

    def test_task_is_registered_in_beat_schedule(self):
        """Расписание из `celery.py` затирает `CELERY_BEAT_SCHEDULE` настроек целиком.

        Регистрация только в `settings/base.py` означает, что задача не
        запустится никогда, и тест на саму функцию этого не покажет.
        """
        from freesport.celery import app

        entries = [e for e in app.conf.beat_schedule.values() if e["task"] == cleanup_stale_exchange_dirs.name]
        assert entries, "Задача уборки обязана попасть в app.conf.beat_schedule"


@pytest.mark.django_db
class TestLockKeepsSerialization:
    """AC6 — очередь за локом каталога обмена сохраняется.

    Non-goal спеки: «не устранять само ожидание лока». Наивная изоляция даёт
    каждой сессии собственный ключ лока и молча снимает сериализацию задач.
    """

    def test_sessions_share_one_lock_key(self, exchange):
        assert _import_lock_key(str(_import_dir("sess-a"))) == _import_lock_key(str(_import_dir("sess-b")))

    def test_manual_dir_keeps_its_own_key(self, tmp_path):
        """Ручной прогон вне каталога обмена ключуется по себе, как и раньше."""
        manual = str(tmp_path / "manual")
        assert _import_lock_key(manual) == f"onec:import:lock:{manual}"

    @patch("apps.products.tasks.call_command")
    def test_second_session_waits_for_the_lock(self, mock_call_command, exchange, clean_cache, settings):
        """Вторая сессия получает Retry с той же формулировкой, потом отрабатывает."""
        session_b = _session("sess-b", ImportSession.ImportStatus.IN_PROGRESS)
        data_dir_b = str(_import_dir("sess-b"))
        Path(data_dir_b).mkdir(parents=True, exist_ok=True)

        cache.add(_import_lock_key(str(_import_dir("sess-a"))), "task-holder", 60)

        with patch.object(process_1c_import_task, "retry", side_effect=Retry()) as mock_retry:
            process_1c_import_task.apply(
                args=(session_b.pk,),
                kwargs={"data_dir": data_dir_b, "source_filename": _segment_name(2)},
                task_id="task-wait",
            )

        mock_retry.assert_called_once()
        mock_call_command.assert_not_called()
        session_b.refresh_from_db()
        assert "Каталог обмена занят другим импортом, задача отложена" in session_b.report

        cache.clear()
        assert (
            process_1c_import_task.apply(
                args=(session_b.pk,),
                kwargs={"data_dir": data_dir_b, "source_filename": _segment_name(2)},
                task_id="task-wait-2",
            ).get()
            == "success"
        )
