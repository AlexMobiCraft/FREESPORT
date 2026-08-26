"""Регрессия гонки cleanup в обмене 1С (инцидент выгрузки 25.08.2026).

Каталог обмена общий для всех сессий, задачи Celery идут параллельно, а
`_cleanup_files` удалял XML по маске `glob("rests/rests*.xml")` — и сносил файлы
соседних задач раньше, чем те успевали их прочитать. Итог на проде: 5 сессий
`failed`, 6 из 16 сегментов остатков не прочитаны никем, две сессии отчитались
`completed` с нулём записей.

Здесь закрыты обе половины исправления:
- точечный cleanup — удаляется только то, что эта команда реально распарсила;
- сериализация `process_1c_import_task` через лок каталога обмена в Redis.

XML берутся из закоммиченного среза реальной выгрузки 1С
(`backend/tests/fixtures/1c-data/`) — синтетику проект запрещает. Сегменты
имитируются побайтовыми копиями реального файла под именами, которые 1С даёт
сегментам: содержимое остаётся настоящим, а число записей в сегменте известно.
"""

from __future__ import annotations

import re
import shutil
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from celery.exceptions import MaxRetriesExceededError, Retry
from django.core.cache import cache
from django.core.management import CommandError, call_command

from apps.integrations.onec_exchange.file_type_detection import detect_file_type
from apps.products.management.commands.import_products_from_1c import Command
from apps.products.models import ImportSession
from apps.products.services.parser import XMLDataParser
from apps.products.services.variant_import import VariantImportProcessor
from apps.products.tasks import _release_import_lock, process_1c_import_task

ONEC_FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "1c-data"
REAL_RESTS_XML = ONEC_FIXTURES / "rests" / "rests.xml"

# Назначенный правилами проекта корпус runtime-выгрузок (в .gitignore, на раннере
# отсутствует) — источник по-настоящему разных сегментов для data_dependent теста.
ONEC_RUNTIME_RESTS = Path(__file__).resolve().parents[3] / "data" / "import_1c" / "rests"

RECORDS_RE = re.compile(r"записей остатков (\d+)")


def _segment_name(index: int) -> str:
    """Имя сегмента в формате, который присылает 1С."""
    return f"rests_1_{index}_00000000-0000-0000-0000-{index:012d}.xml"


def _make_exchange_dir(base: Path) -> Path:
    """Каталог обмена с пустой подпапкой rests."""
    data_dir = base / "1c_import"
    (data_dir / "rests").mkdir(parents=True)
    return data_dir


def _stage_segment(data_dir: Path, index: int) -> Path:
    """Положить в каталог обмена очередной сегмент остатков."""
    target = data_dir / "rests" / _segment_name(index)
    shutil.copyfile(REAL_RESTS_XML, target)
    return target


def _run_import(data_dir: Path, session: ImportSession) -> str:
    """Прогон команды импорта остатков поверх существующей сессии."""
    out = StringIO()
    call_command(
        "import_products_from_1c",
        data_dir=str(data_dir),
        file_type="rests",
        import_session_id=session.pk,
        stdout=out,
        stderr=StringIO(),
    )
    return out.getvalue()


def _records_in(output: str) -> int:
    return sum(int(m) for m in RECORDS_RE.findall(output))


@pytest.fixture
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestPinpointCleanup:
    """AC1 — удаляются только файлы, которые эта команда действительно распарсила."""

    def test_neighbour_file_survives_cleanup(self, tmp_path):
        """Сосед положил свой сегмент до cleanup — он обязан уцелеть."""
        data_dir = _make_exchange_dir(tmp_path)
        own = _stage_segment(data_dir, 1)
        neighbour = data_dir / "rests" / _segment_name(2)

        session = ImportSession.objects.create(status=ImportSession.ImportStatus.IN_PROGRESS)

        original_finalize = VariantImportProcessor.finalize_session

        def stage_neighbour(processor, *args, **kwargs):
            # Момент гонки: сосед принял файл между сбором списка и cleanup.
            shutil.copyfile(REAL_RESTS_XML, neighbour)
            return original_finalize(processor, *args, **kwargs)

        with patch.object(VariantImportProcessor, "finalize_session", stage_neighbour):
            _run_import(data_dir, session)

        assert not own.exists(), "Свой распарсенный сегмент должен быть удалён"
        assert neighbour.exists(), "Чужой сегмент удалять нельзя — это и есть дефект"

    def test_cleanup_counts_only_processed_files(self, tmp_path):
        """Счётчик удалённых XML не может превышать число распарсенных файлов."""
        data_dir = _make_exchange_dir(tmp_path)
        _stage_segment(data_dir, 1)
        _stage_segment(data_dir, 2)

        session = ImportSession.objects.create(status=ImportSession.ImportStatus.IN_PROGRESS)
        output = _run_import(data_dir, session)

        match = re.search(r"Удалено XML файлов: (\d+)", output)
        assert match is not None
        assert int(match.group(1)) == 2

    def test_cleanup_files_ignores_unparsed_neighbours(self, tmp_path):
        """`_cleanup_files` без списка обработанного не удаляет ничего."""
        data_dir = _make_exchange_dir(tmp_path)
        stranger = _stage_segment(data_dir, 7)

        command = Command()
        command.stdout = StringIO()
        command._cleanup_files(str(data_dir), "rests", [])

        assert stranger.exists()


@pytest.mark.django_db
class TestMissingFileResilience:
    """AC3 — исчезнувший файл не валит импорт целиком."""

    def _run_with_vanishing(self, data_dir: Path, session: ImportSession, vanish: set[int]) -> str:
        """Прогон, где перечисленные сегменты исчезают между сбором и парсингом."""
        original_parse = XMLDataParser.parse_rests_xml

        def parse_or_vanish(parser, file_path):
            for index in vanish:
                if _segment_name(index) == Path(file_path).name:
                    Path(file_path).unlink(missing_ok=True)
            return original_parse(parser, file_path)

        with patch.object(XMLDataParser, "parse_rests_xml", parse_or_vanish):
            return _run_import(data_dir, session)

    def test_partial_loss_completes_and_reports(self, tmp_path):
        """Один файл из трёх исчез: два обработаны, сессия COMPLETED."""
        data_dir = _make_exchange_dir(tmp_path)
        for index in (1, 2, 3):
            _stage_segment(data_dir, index)

        session = ImportSession.objects.create(status=ImportSession.ImportStatus.IN_PROGRESS)
        output = self._run_with_vanishing(data_dir, session, vanish={2})

        session.refresh_from_db()
        assert session.status == ImportSession.ImportStatus.COMPLETED
        assert len(RECORDS_RE.findall(output)) == 2
        assert _segment_name(2) in session.report

    def test_total_loss_fails_instead_of_silent_success(self, tmp_path):
        """Исчезли все файлы: FAILED с перечнем, а не COMPLETED с нулём записей."""
        data_dir = _make_exchange_dir(tmp_path)
        for index in (1, 2, 3):
            _stage_segment(data_dir, index)

        session = ImportSession.objects.create(status=ImportSession.ImportStatus.IN_PROGRESS)

        with pytest.raises(CommandError):
            self._run_with_vanishing(data_dir, session, vanish={1, 2, 3})

        session.refresh_from_db()
        assert session.status == ImportSession.ImportStatus.FAILED
        assert _segment_name(1) in session.error_message

    def test_no_files_at_all_keeps_current_behaviour(self, tmp_path):
        """Файлов типа нет изначально — прежнее поведение: предупреждение и успех."""
        data_dir = _make_exchange_dir(tmp_path)
        session = ImportSession.objects.create(status=ImportSession.ImportStatus.IN_PROGRESS)

        output = _run_import(data_dir, session)

        session.refresh_from_db()
        assert session.status == ImportSession.ImportStatus.COMPLETED
        assert "Файлы rests.xml не найдены" in output


@pytest.mark.django_db
class TestCleanupRaceRegression:
    """AC8 — восемь наложенных сессий не теряют ни одного сегмента."""

    SESSIONS = 8

    def test_eight_overlapping_sessions_lose_nothing(self, tmp_path):
        data_dir = _make_exchange_dir(tmp_path)
        _stage_segment(data_dir, 1)

        original_finalize = VariantImportProcessor.finalize_session
        staged = {"next": 2}

        def stage_next(processor, *args, **kwargs):
            # Сосед кладёт следующий сегмент ровно в окно между сбором списка
            # и cleanup текущей команды — так и выглядела выгрузка 25.08.2026.
            if staged["next"] <= TestCleanupRaceRegression.SESSIONS:
                _stage_segment(data_dir, staged["next"])
                staged["next"] += 1
            return original_finalize(processor, *args, **kwargs)

        total_records = 0
        sessions = []
        with patch.object(VariantImportProcessor, "finalize_session", stage_next):
            for _ in range(self.SESSIONS):
                session = ImportSession.objects.create(status=ImportSession.ImportStatus.IN_PROGRESS)
                sessions.append(session)
                total_records += _records_in(_run_import(data_dir, session))

        statuses = [ImportSession.objects.get(pk=s.pk).status for s in sessions]
        assert ImportSession.ImportStatus.FAILED not in statuses

        # Эталон: сколько записей в одном сегменте при изолированном прогоне.
        probe_dir = _make_exchange_dir(tmp_path / "probe")
        _stage_segment(probe_dir, 1)
        probe_session = ImportSession.objects.create(status=ImportSession.ImportStatus.IN_PROGRESS)
        expected_per_file = _records_in(_run_import(probe_dir, probe_session))

        assert expected_per_file > 0
        assert total_records == expected_per_file * self.SESSIONS

    @pytest.mark.data_dependent
    def test_real_runtime_segments_lose_nothing(self, tmp_path):
        """То же самое на реально разных сегментах назначенного корпуса."""
        if not ONEC_RUNTIME_RESTS.exists():
            pytest.skip("Назначенный корпус data/import_1c отсутствует (в .gitignore)")

        segments = sorted(ONEC_RUNTIME_RESTS.glob("rests_1_*.xml"))
        if len(segments) < 2:
            pytest.skip("Недостаточно сегментов остатков в назначенном корпусе")

        data_dir = _make_exchange_dir(tmp_path)
        shutil.copyfile(segments[0], data_dir / "rests" / segments[0].name)

        original_finalize = VariantImportProcessor.finalize_session
        staged = {"next": 1}

        def stage_next(processor, *args, **kwargs):
            if staged["next"] < len(segments):
                nxt = segments[staged["next"]]
                shutil.copyfile(nxt, data_dir / "rests" / nxt.name)
                staged["next"] += 1
            return original_finalize(processor, *args, **kwargs)

        seen = 0
        with patch.object(VariantImportProcessor, "finalize_session", stage_next):
            for _ in segments:
                session = ImportSession.objects.create(status=ImportSession.ImportStatus.IN_PROGRESS)
                seen += len(RECORDS_RE.findall(_run_import(data_dir, session)))

        assert seen == len(segments), "Каждый сегмент обязан быть прочитан ровно один раз"


class TestDetectFileType:
    """AC4 — единая логика определения типа файла для задачи и оркестратора."""

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("goods_1_1_abc.xml", "goods"),
            ("import.xml", "goods"),
            ("propertiesGoods_1_1.xml", "goods"),
            ("offers_1_3_abc.xml", "offers"),
            ("prices_1_2_abc.xml", "prices"),
            ("priceLists.xml", "prices"),
            ("rests_1_16_5e505506.xml", "rests"),
            ("complete", "all"),
            ("unknown.xml", "all"),
            ("", "all"),
            (None, "all"),
        ],
    )
    def test_detect_file_type(self, filename, expected):
        assert detect_file_type(filename) == expected


@pytest.mark.django_db
class TestOrchestratorPassesFilename:
    """AC4 — обе точки диспатча передают имя файла в задачу."""

    def _orchestrator(self, tmp_path, filename):
        from apps.integrations.onec_exchange.import_orchestrator import ImportOrchestratorService

        service = ImportOrchestratorService("sess-1", filename)
        service.import_dir = tmp_path / "1c_import"
        service.import_dir.mkdir(parents=True, exist_ok=True)
        return service

    def test_dispatch_import_passes_source_filename(self, tmp_path):
        service = self._orchestrator(tmp_path, "rests_1_16_5e505506.xml")
        session = ImportSession.objects.create(status=ImportSession.ImportStatus.PENDING)

        with patch("apps.products.tasks.process_1c_import_task.delay") as mock_delay:
            service._dispatch_import(session)

        assert mock_delay.call_args.kwargs["source_filename"] == "rests_1_16_5e505506.xml"

    def test_dispatch_or_dryrun_passes_source_filename(self, tmp_path):
        service = self._orchestrator(tmp_path, "complete")
        session = ImportSession.objects.create(status=ImportSession.ImportStatus.PENDING)

        with (
            patch("apps.products.tasks.process_1c_import_task.delay") as mock_delay,
            patch("apps.integrations.onec_exchange.import_orchestrator.FileStreamService"),
        ):
            service._dispatch_or_dryrun(session, dry_run=False)

        assert mock_delay.call_args.kwargs["source_filename"] == "complete"

    def test_complete_mode_still_means_all(self, tmp_path):
        service = self._orchestrator(tmp_path, "complete")
        assert service._detect_file_type() == "all"


@pytest.mark.django_db
class TestImportDirectoryLock:
    """AC2 — на каталог обмена одновременно работает ровно одна задача."""

    @staticmethod
    def _lock_key(data_dir: str) -> str:
        return f"onec:import:lock:{data_dir}"

    @patch("apps.products.tasks.call_command")
    def test_lock_taken_and_released(self, mock_call_command, clean_cache, tmp_path):
        data_dir = str(tmp_path / "1c_import")
        Path(data_dir).mkdir(parents=True)
        session = ImportSession.objects.create(status=ImportSession.ImportStatus.PENDING)

        seen = {}

        def capture(*args, **kwargs):
            seen["locked"] = cache.get(self._lock_key(data_dir))

        mock_call_command.side_effect = capture

        result = process_1c_import_task.apply(
            args=(session.id,), kwargs={"data_dir": data_dir}, task_id="task-lock-1"
        ).get()

        assert result == "success"
        assert seen["locked"] == "task-lock-1", "Во время импорта лок обязан принадлежать задаче"
        assert cache.get(self._lock_key(data_dir)) is None, "Лок обязан сниматься в finally"

    @patch("apps.products.tasks.call_command")
    def test_lock_released_on_failure(self, mock_call_command, clean_cache, tmp_path):
        data_dir = str(tmp_path / "1c_import")
        Path(data_dir).mkdir(parents=True)
        mock_call_command.side_effect = Exception("boom")
        session = ImportSession.objects.create(status=ImportSession.ImportStatus.PENDING)

        process_1c_import_task.apply(args=(session.id,), kwargs={"data_dir": data_dir}, task_id="task-lock-2").get()

        assert cache.get(self._lock_key(data_dir)) is None

    @patch("apps.products.tasks.call_command")
    def test_busy_lock_retries_without_touching_session(self, mock_call_command, clean_cache, tmp_path, settings):
        data_dir = str(tmp_path / "1c_import")
        Path(data_dir).mkdir(parents=True)
        cache.add(self._lock_key(data_dir), "other-task", 60)

        session = ImportSession.objects.create(status=ImportSession.ImportStatus.IN_PROGRESS)

        with patch.object(process_1c_import_task, "retry", side_effect=Retry()) as mock_retry:
            process_1c_import_task.apply(args=(session.id,), kwargs={"data_dir": data_dir}, task_id="task-lock-3")

        mock_retry.assert_called_once()
        assert mock_retry.call_args.kwargs["countdown"] == settings.ONEC_IMPORT_LOCK_RETRY_COUNTDOWN
        assert mock_retry.call_args.kwargs["max_retries"] == settings.ONEC_IMPORT_LOCK_MAX_RETRIES

        mock_call_command.assert_not_called()

        session.refresh_from_db()
        assert session.status == ImportSession.ImportStatus.IN_PROGRESS
        assert cache.get(self._lock_key(data_dir)) == "other-task", "Чужой лок трогать нельзя"

    @patch("apps.products.tasks.call_command")
    def test_max_retries_marks_session_failed(self, mock_call_command, clean_cache, tmp_path):
        data_dir = str(tmp_path / "1c_import")
        Path(data_dir).mkdir(parents=True)
        cache.add(self._lock_key(data_dir), "other-task", 60)

        session = ImportSession.objects.create(status=ImportSession.ImportStatus.IN_PROGRESS)

        with patch.object(process_1c_import_task, "retry", side_effect=MaxRetriesExceededError()):
            result = process_1c_import_task.apply(
                args=(session.id,), kwargs={"data_dir": data_dir}, task_id="task-lock-4"
            ).get()

        assert result == "failure"
        session.refresh_from_db()
        assert session.status == ImportSession.ImportStatus.FAILED
        assert session.error_message

    def test_lock_ttl_is_configured(self, settings):
        """Упавший воркер не блокирует обмен навсегда — лок живёт по TTL из настроек."""
        assert settings.ONEC_IMPORT_LOCK_TTL > 0

    def test_release_lock_only_by_owner(self, clean_cache):
        key = "onec:import:lock:/tmp/whatever"
        cache.add(key, "owner-a", 60)

        _release_import_lock(key, "owner-b")
        assert cache.get(key) == "owner-a", "Чужой лок снимать нельзя"

        _release_import_lock(key, "owner-a")
        assert cache.get(key) is None


@pytest.mark.django_db
class TestTaskUsesSourceFilename:
    """AC4 — сегмент остатков запускает только шаг остатков."""

    @patch("apps.products.tasks.call_command")
    def test_source_filename_drives_file_type(self, mock_call_command, clean_cache, tmp_path):
        data_dir = str(tmp_path / "1c_import")
        Path(data_dir).mkdir(parents=True)
        session = ImportSession.objects.create(status=ImportSession.ImportStatus.PENDING)

        process_1c_import_task.apply(
            args=(session.id,),
            kwargs={"data_dir": data_dir, "source_filename": "rests_1_16_5e505506.xml"},
            task_id="task-ft-1",
        ).get()

        assert mock_call_command.call_args.kwargs["file_type"] == "rests"

    @patch("apps.products.tasks.call_command")
    def test_without_source_filename_stays_all(self, mock_call_command, clean_cache, tmp_path):
        data_dir = str(tmp_path / "1c_import")
        Path(data_dir).mkdir(parents=True)
        session = ImportSession.objects.create(status=ImportSession.ImportStatus.PENDING)

        process_1c_import_task.apply(args=(session.id,), kwargs={"data_dir": data_dir}, task_id="task-ft-2").get()

        assert mock_call_command.call_args.kwargs["file_type"] == "all"
