"""Database backups with pg_dump, kept outside Docker and rotated by count."""

import os
import subprocess
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

PREFIX = "radar-"
SUFFIX = ".dump"
# Fixed-width timestamps, so sorting file names sorts backups by age.
TIMESTAMP = "%Y-%m-%d-%H%M%S"
OFFSITE_NAME = "radar-offsite.dump.age"
OFFSITE_MAX_AGE = timedelta(days=7)


def dump_command() -> list[str]:
    """pg_dump inside the db container: the same version as the server, and the
    container's local socket needs no password."""
    return [
        "docker", "compose", "exec", "-T", "db", "pg_dump",
        "--username", os.environ.get("POSTGRES_USER", "postgres"),
        "--dbname", os.environ.get("POSTGRES_DB", "radar"),
        "--format", "custom",
        "--compress", "zstd",
    ]  # fmt: skip


def encrypt_command(recipient: str, source: Path, output: Path) -> list[str]:
    """age encrypts to a public key, so the nightly run needs no secret; only
    the private key, kept off this computer, can decrypt the copy."""
    return [
        "age", "--encrypt",
        "--recipient", recipient,
        "--output", str(output),
        str(source),
    ]  # fmt: skip


def _publish(target: Path, write: Callable[[Path], None]) -> Path:
    """Write under a .partial name and rename to `target` only once the write
    succeeds, so an interrupted write never looks like a good backup."""
    partial = target.with_name(target.name + ".partial")
    try:
        write(partial)
        partial.replace(target)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return target


def create_backup(directory: Path, command: list[str], now: datetime) -> Path:
    def dump(partial: Path) -> None:
        with partial.open("wb") as out:
            subprocess.run(command, stdout=out, check=True)

    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{PREFIX}{now.strftime(TIMESTAMP)}{SUFFIX}"
    # Two runs within one second would otherwise overwrite a good backup.
    if target.exists():
        raise FileExistsError(f"{target} already exists")
    return _publish(target, dump)


def prune(directory: Path, keep: int) -> list[Path]:
    """Delete all but the newest `keep` backups and return the deleted paths.

    Counting backups instead of days means days with the computer off do not
    use up the copies. Other files in the directory are left alone.
    """
    if keep < 1:
        raise ValueError("keep must be at least 1")
    old = sorted(directory.glob(f"{PREFIX}*{SUFFIX}"))[:-keep]
    for path in old:
        path.unlink()
    return old


def offsite_due(path: Path, now: datetime) -> bool:
    if not path.exists():
        return True
    return now - datetime.fromtimestamp(path.stat().st_mtime) > OFFSITE_MAX_AGE


def refresh_offsite(directory: Path, backup: Path, recipient: str) -> Path:
    """Replace the single encrypted copy that leaves the computer."""
    directory.mkdir(parents=True, exist_ok=True)
    return _publish(
        directory / OFFSITE_NAME,
        lambda partial: subprocess.run(
            encrypt_command(recipient, backup, partial), check=True
        ),
    )


def db_ready() -> bool:
    command = [
        "docker", "compose", "exec", "-T", "db", "pg_isready",
        "--username", os.environ.get("POSTGRES_USER", "postgres"),
        "--dbname", os.environ.get("POSTGRES_DB", "radar"),
    ]  # fmt: skip
    return subprocess.run(command, capture_output=True).returncode == 0


def wait_for_db(
    ready: Callable[[], bool],
    timeout: float,
    interval: float = 5,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Right after the computer starts, Docker may still be starting the
    database, so a scheduled backup waits for it instead of failing at once."""
    deadline = clock() + timeout
    while not ready():
        if clock() >= deadline:
            raise TimeoutError(f"the database was not ready within {timeout:g} s")
        sleep(interval)


def run() -> int:
    """`radar backup`: dump into BACKUP_DIR/recent, rotate, and refresh the
    encrypted copy in BACKUP_DIR/offsite once it is older than a week."""
    root = _backup_dir()
    keep = int(os.environ.get("BACKUP_KEEP", "3"))
    recipient = os.environ.get("BACKUP_AGE_RECIPIENT")
    warn_mb = float(os.environ.get("BACKUP_OFFSITE_WARN_MB", "1024"))
    wait = float(os.environ.get("BACKUP_WAIT_SECONDS", "300"))
    offsite = root / "offsite" / OFFSITE_NAME
    started = datetime.now()
    notes = []
    try:
        wait_for_db(db_ready, wait)
        path = create_backup(root / "recent", dump_command(), started)
        notes.append(f"ok {path.name} {_kb(path)}")
        notes.append(f"deleted {len(prune(path.parent, keep))}")
        if not recipient:
            notes.append("offsite skipped: BACKUP_AGE_RECIPIENT is not set")
        elif offsite_due(offsite, started):
            refresh_offsite(offsite.parent, path, recipient)
            notes.append(f"offsite {_kb(offsite)}")
            if offsite.stat().st_size > warn_mb * 1024 * 1024:
                notes.append(f"warning: offsite copy is over {warn_mb:g} MB")
        else:
            notes.append("offsite not due")
    except BaseException as error:
        notes.append(f"failed: {error!r}")
        raise
    finally:
        _log(root / "backup.log", started, ", ".join(notes))
    print(", ".join(notes))
    return 0


def backup_before_migration() -> Path:
    """A copy in BACKUP_DIR/pre-migration that is never rotated away, because a
    broken migration may be noticed only after several nightly backups."""
    root = _backup_dir()
    started = datetime.now()
    try:
        path = create_backup(root / "pre-migration", dump_command(), started)
    except BaseException as error:
        _log(root / "backup.log", started, f"pre-migration failed: {error!r}")
        raise
    _log(root / "backup.log", started, f"pre-migration {path.name} {_kb(path)}")
    return path


def _backup_dir() -> Path:
    root = os.environ.get("BACKUP_DIR")
    if not root:
        raise RuntimeError(
            "BACKUP_DIR is not set; load .env with `uv run --env-file .env ...`"
        )
    return Path(root)


def _kb(path: Path) -> str:
    return f"{path.stat().st_size / 1024:.1f} KB"


def _log(log: Path, started: datetime, message: str) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as out:
        out.write(f"{started:%Y-%m-%d %H:%M:%S} {message}\n")
