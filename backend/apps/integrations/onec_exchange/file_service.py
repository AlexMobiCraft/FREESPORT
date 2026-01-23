"""
File Stream Service for 1C Exchange.

Provides memory-efficient file operations for handling large binary uploads
from 1C Enterprise system using chunked transfer.

Story 2.1: File Stream Upload
"""
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Generator, Union

from django.conf import settings

logger = logging.getLogger(__name__)

# File permissions: owner read/write, group/others read-only
DEFAULT_FILE_MODE = 0o644

# Lock acquisition settings
LOCK_TIMEOUT_SECONDS = 30
LOCK_RETRY_INTERVAL = 0.1


class FileLockError(Exception):
    """Raised when file lock cannot be acquired."""
    pass


class FileLock:
    """
    Cross-platform file locking using lock files.

    Uses exclusive file creation (O_EXCL) to ensure atomic lock acquisition.
    This works on both Windows and Linux without external dependencies.

    Usage:
        lock = FileLock(Path("/tmp/myfile.lock"))
        with lock:
            # exclusive access to protected resource
            ...
    """

    def __init__(self, lock_path: Path, timeout: float = LOCK_TIMEOUT_SECONDS):
        self.lock_path = lock_path
        self.timeout = timeout
        self._acquired = False

    def acquire(self) -> bool:
        """
        Acquire the file lock, waiting up to timeout seconds.

        Returns:
            True if lock acquired

        Raises:
            FileLockError: If lock cannot be acquired within timeout
        """
        start = time.time()

        while time.time() - start < self.timeout:
            try:
                # O_CREAT | O_EXCL ensures atomic creation - fails if file exists
                fd = os.open(
                    str(self.lock_path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
                os.close(fd)
                self._acquired = True
                logger.debug(f"Lock acquired: {self.lock_path}")
                return True
            except FileExistsError:
                time.sleep(LOCK_RETRY_INTERVAL)
            except OSError as e:
                # Handle permission errors or other OS-level issues
                logger.warning(f"Lock acquisition error: {e}")
                time.sleep(LOCK_RETRY_INTERVAL)

        raise FileLockError(
            f"Could not acquire lock within {self.timeout}s: {self.lock_path}"
        )

    def release(self) -> None:
        """Release the file lock by removing the lock file."""
        if self._acquired:
            try:
                os.unlink(str(self.lock_path))
                logger.debug(f"Lock released: {self.lock_path}")
            except FileNotFoundError:
                # Lock file already removed - that's fine
                pass
            except OSError as e:
                logger.warning(f"Error releasing lock: {e}")
            finally:
                self._acquired = False

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


class FileWriter:
    """
    Writer wrapper for tracking bytes written during streaming upload.

    Used with FileStreamService.open_for_write() context manager.
    """

    def __init__(self, file_handle: IO[bytes]):
        self._file = file_handle
        self.bytes_written = 0

    def write(self, data: bytes) -> int:
        """Write data and track bytes written."""
        written = self._file.write(data)
        self.bytes_written += len(data)
        return written


class FileStreamService:
    """
    Service for handling chunked file uploads from 1C.
    
    Files are isolated per session to prevent collisions:
    MEDIA_ROOT/1c_temp/<session_id>/<filename>
    
    Usage:
        service = FileStreamService(session_id)
        bytes_written = service.append_chunk('import.zip', binary_content)
    """
    
    def __init__(self, session_id: str):
        """
        Initialize service for a specific session.
        
        Args:
            session_id: Django session key for isolation
        """
        if not session_id:
            raise ValueError("session_id is required for FileStreamService")
        
        self.session_id = session_id
        self.base_dir: Path = settings.ONEC_EXCHANGE.get(
            'TEMP_DIR', 
            Path(settings.MEDIA_ROOT) / '1c_temp'
        )
        self.session_dir = self.base_dir / session_id
    
    def _ensure_session_dir(self) -> Path:
        """
        Create session-specific directory if it doesn't exist.
        
        Returns:
            Path to session directory
        """
        self.session_dir.mkdir(parents=True, exist_ok=True)
        return self.session_dir
    
    def get_file_path(self, filename: str) -> Path:
        """
        Get full path for a file within the session directory.
        
        Args:
            filename: Name of the file
            
        Returns:
            Full path to the file
        """
        # Sanitize filename to prevent directory traversal
        safe_filename = Path(filename).name
        return self.session_dir / safe_filename
    
    def append_chunk(self, filename: str, content: Union[bytes, memoryview]) -> int:
        """
        Append binary content to a file.
        
        Uses 'ab' (append binary) mode to support chunked uploads.
        If file doesn't exist, it will be created.
        
        Args:
            filename: Name of the file to append to
            content: Binary content to append
            
        Returns:
            Number of bytes written
        """
        self._ensure_session_dir()
        file_path = self.get_file_path(filename)
        
        bytes_written = len(content)
        
        with open(file_path, 'ab') as f:
            f.write(content)
        
        logger.info(
            f"Appended {bytes_written} bytes to {file_path.name} "
            f"(session: {self.session_id[:8]}...)"
        )
        
        return bytes_written
    
    def get_file_size(self, filename: str) -> int:
        """
        Get current size of a file.
        
        Args:
            filename: Name of the file
            
        Returns:
            File size in bytes, or 0 if file doesn't exist
        """
        file_path = self.get_file_path(filename)
        if file_path.exists():
            return file_path.stat().st_size
        return 0
    
    def file_exists(self, filename: str) -> bool:
        """
        Check if a file exists in the session directory.
        
        Args:
            filename: Name of the file
            
        Returns:
            True if file exists
        """
        return self.get_file_path(filename).exists()
    
    def list_files(self) -> list[str]:
        """
        List all files in the session directory.
        
        Returns:
            List of filenames
        """
        if not self.session_dir.exists():
            return []
        return [f.name for f in self.session_dir.iterdir() if f.is_file()]
    
    def cleanup_session(self) -> int:
        """
        Remove all files in the session directory.

        Called during 'init' mode to ensure clean slate for new imports.
        Prevents stale file accumulation from previous/failed uploads.

        Returns:
            Number of files deleted
        """
        if not self.session_dir.exists():
            return 0

        deleted_count = 0
        for file_path in self.session_dir.iterdir():
            if file_path.is_file():
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted temp file: {file_path.name}")
                except OSError as e:
                    logger.warning(f"Failed to delete {file_path.name}: {e}")

        logger.info(
            f"Session cleanup: deleted {deleted_count} files "
            f"(session: {self.session_id[:8]}...)"
        )
        return deleted_count

    @contextmanager
    def open_for_write(self, filename: str) -> Generator[FileWriter, None, None]:
        """
        Context manager for efficient streaming file writes.

        Opens the file once for the entire upload, avoiding repeated
        open/close cycles for each chunk. Uses append mode to support
        chunked uploads across multiple HTTP requests.

        File locking prevents corruption during concurrent uploads to the
        same file (e.g., interleaved chunked uploads from 1C).

        Usage:
            with service.open_for_write('import.zip') as writer:
                writer.write(chunk1)
                writer.write(chunk2)
            total = writer.bytes_written

        Args:
            filename: Name of the file to write

        Yields:
            FileWriter instance with write() method and bytes_written counter

        Raises:
            FileLockError: If file lock cannot be acquired within timeout
        """
        self._ensure_session_dir()
        file_path = self.get_file_path(filename)
        lock_path = file_path.with_suffix(file_path.suffix + '.lock')

        writer = None
        lock = FileLock(lock_path)

        try:
            # Acquire exclusive lock before opening file
            lock.acquire()

            # Open file with explicit permissions (0o644)
            # Use os.open for permission control, then wrap with Python file object
            fd = os.open(
                str(file_path),
                os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                DEFAULT_FILE_MODE
            )
            try:
                with os.fdopen(fd, 'ab') as f:
                    writer = FileWriter(f)
                    yield writer
            except Exception:
                # fd is closed by fdopen, but if fdopen fails we need to close fd
                try:
                    os.close(fd)
                except OSError:
                    pass
                raise
        finally:
            # Always release lock, even on exception
            lock.release()

            if writer:
                logger.info(
                    f"Wrote {writer.bytes_written} bytes to {file_path.name} "
                    f"(session: {self.session_id[:8]}...)"
                )
