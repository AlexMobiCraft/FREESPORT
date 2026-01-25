"""
File Routing Service for 1C Exchange.

Routes uploaded files to appropriate directories based on file type:
- XML files (goods, offers, prices, rests, groups) -> 1c_import/<sessid>/<type>/
- Images (jpg, jpeg, png, gif, webp) -> 1c_import/<sessid>/import_files/
- ZIP files -> NOT routed (stays in temp for later unpacking)
- Other files -> 1c_import/<sessid>/ (root)

Story 2.2: Сохранение файлов и маршрутизация
"""
import logging
import shutil
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

# Routing rules for XML files based on filename prefix
XML_ROUTING_RULES = {
    "goods": "goods/",
    "offers": "offers/",
    "prices": "prices/",
    "rests": "rests/",
    "groups": "groups/",
    "priceLists": "priceLists/",
    "propertiesGoods": "propertiesGoods/",
    "propertiesOffers": "propertiesOffers/",
    "contragents": "contragents/",
    "storages": "storages/",
    "units": "units/",
}

# Supported image extensions (case-insensitive)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# ZIP extensions that should NOT be routed
ZIP_EXTENSIONS = {".zip"}


class FileRoutingService:
    """
    Service for routing uploaded files to appropriate import directories.

    Files are isolated per session to prevent collisions:
    MEDIA_ROOT/1c_import/<session_id>/<subdir>/<filename>

    Usage:
        router = FileRoutingService(session_id)
        if router.should_route(filename):
            target_path = router.move_to_import(filename)
    """

    def __init__(self, session_id: str):
        """
        Initialize service for a specific session.

        Args:
            session_id: Django session key for isolation

        Raises:
            ValueError: If session_id is empty
        """
        if not session_id:
            raise ValueError("session_id is required for FileRoutingService")

        self.session_id = session_id

        # Get directories from settings
        self.temp_base: Path = settings.ONEC_EXCHANGE.get(
            "TEMP_DIR", Path(settings.MEDIA_ROOT) / "1c_temp"
        )
        self.import_base: Path = settings.ONEC_EXCHANGE.get(
            "IMPORT_DIR", Path(settings.MEDIA_ROOT) / "1c_import"
        )

        self.temp_dir = self.temp_base / session_id
        self.import_dir = self.import_base / session_id

    def _get_temp_file_path(self, filename: str) -> Path:
        """
        Get path to file in temp directory.

        Args:
            filename: Name of the file

        Returns:
            Full path to file in temp directory
        """
        safe_filename = Path(filename).name
        return self.temp_dir / safe_filename

    def _ensure_import_dir(self, subdir: str = "") -> Path:
        """
        Create import directory (with optional subdirectory) if it doesn't exist.

        Args:
            subdir: Optional subdirectory within session import folder

        Returns:
            Path to the directory
        """
        target_dir = self.import_dir
        if subdir:
            target_dir = target_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def route_file(self, filename: str) -> str:
        """
        Determine the target subdirectory for a file based on its name/extension.

        Args:
            filename: Name of the file

        Returns:
            Subdirectory name (e.g., 'goods/', 'import_files/').
            Returns empty string ('') to indicate the file should be placed in
            the root of the session import directory (1c_import/<sessid>/).
        """
        safe_filename = Path(filename).name
        suffix = Path(safe_filename).suffix.lower()
        name_lower = safe_filename.lower()

        # Check XML routing rules by prefix
        if suffix == ".xml":
            for prefix, subdir in XML_ROUTING_RULES.items():
                if name_lower.startswith(prefix):
                    return subdir.rstrip("/")
            # Unknown XML file -> root
            return ""

        # Check image extensions
        if suffix in IMAGE_EXTENSIONS:
            return "import_files"

        # Other unknown files -> root
        return ""

    def should_route(self, filename: str) -> bool:
        """
        Determine if a file should be routed (moved to import directory).

        ZIP files are NOT routed - they stay in temp for later unpacking.

        Args:
            filename: Name of the file

        Returns:
            True if file should be routed, False for ZIP files
        """
        safe_filename = Path(filename).name
        suffix = Path(safe_filename).suffix.lower()

        # ZIP files stay in temp
        if suffix in ZIP_EXTENSIONS:
            return False

        return True

    def move_to_import(self, filename: str) -> Path:
        """
        Move a file from temp directory to appropriate import subdirectory.

        Args:
            filename: Name of the file in temp directory

        Returns:
            Path to the file in its new location

        Raises:
            FileNotFoundError: If source file doesn't exist
        """
        source_path = self._get_temp_file_path(filename)

        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Determine target subdirectory
        subdir = self.route_file(filename)
        target_dir = self._ensure_import_dir(subdir)

        # Target file path
        target_path = target_dir / Path(filename).name

        # Move file (overwrites if exists)
        shutil.move(str(source_path), str(target_path))

        logger.info(
            f"Routed file: {filename} -> {subdir or 'root'} "
            f"(session: {self.session_id[:8]}...)"
        )

        return target_path
