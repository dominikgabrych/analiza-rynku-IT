"""Backup files and rotation, with a stand-in for pg_dump: no Docker needed."""

import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta

import pytest

from radar.backup import (
    create_backup,
    offsite_due,
    prune,
    refresh_offsite,
    wait_for_db,
)

NOW = datetime(2026, 10, 29, 3, 15, 0)


def fake_dump(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def test_backup_is_written_under_its_final_name(tmp_path):
    path = create_backup(
        tmp_path, fake_dump("import sys; sys.stdout.write('dump')"), NOW
    )

    assert path.name == "radar-2026-10-29-031500.dump"
    assert path.read_text() == "dump"
    assert [p.name for p in tmp_path.iterdir()] == [path.name]


def test_failed_dump_leaves_no_file(tmp_path):
    command = fake_dump("import sys; sys.stdout.write('half'); sys.exit(1)")

    with pytest.raises(subprocess.CalledProcessError):
        create_backup(tmp_path, command, NOW)

    assert list(tmp_path.iterdir()) == []


def test_backup_never_overwrites_an_existing_one(tmp_path):
    create_backup(tmp_path, fake_dump("import sys; sys.stdout.write('first')"), NOW)

    with pytest.raises(FileExistsError):
        create_backup(
            tmp_path, fake_dump("import sys; sys.stdout.write('second')"), NOW
        )

    assert (tmp_path / "radar-2026-10-29-031500.dump").read_text() == "first"


def touch(directory, *names):
    for name in names:
        (directory / name).write_text("")


def test_prune_keeps_the_newest_backups(tmp_path):
    touch(
        tmp_path,
        "radar-2026-10-25-031500.dump",
        "radar-2026-10-26-031500.dump",
        "radar-2026-10-27-031500.dump",
        # Days off in between do not matter: copies are counted, not days.
        "radar-2026-11-02-031500.dump",
        "radar-2026-11-02-184000.dump",
    )

    deleted = prune(tmp_path, keep=3)

    assert [p.name for p in deleted] == [
        "radar-2026-10-25-031500.dump",
        "radar-2026-10-26-031500.dump",
    ]
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "radar-2026-10-27-031500.dump",
        "radar-2026-11-02-031500.dump",
        "radar-2026-11-02-184000.dump",
    ]


def test_prune_leaves_other_files_alone(tmp_path):
    touch(
        tmp_path,
        "radar-2026-10-25-031500.dump",
        "radar-2026-10-26-031500.dump.partial",
        "notes.txt",
    )

    assert prune(tmp_path, keep=1) == []
    assert len(list(tmp_path.iterdir())) == 3


def test_prune_never_deletes_every_backup(tmp_path):
    touch(tmp_path, "radar-2026-10-25-031500.dump")

    with pytest.raises(ValueError):
        prune(tmp_path, keep=0)
    assert (tmp_path / "radar-2026-10-25-031500.dump").exists()


def test_offsite_copy_is_due_when_missing_or_older_than_a_week(tmp_path):
    copy = tmp_path / "radar-offsite.dump.age"
    assert offsite_due(copy, NOW)

    copy.write_text("")
    six_days_ago = (NOW - timedelta(days=6)).timestamp()
    os.utime(copy, (six_days_ago, six_days_ago))
    assert not offsite_due(copy, NOW)

    eight_days_ago = (NOW - timedelta(days=8)).timestamp()
    os.utime(copy, (eight_days_ago, eight_days_ago))
    assert offsite_due(copy, NOW)


@pytest.fixture
def identity(tmp_path):
    """A throwaway age key pair: returns the private key file and the public key."""
    if not shutil.which("age"):
        if os.environ.get("CI"):
            pytest.fail(
                "age must be installed in CI, or the encryption tests never run"
            )
        pytest.skip("age is not installed")
    key = tmp_path / "key.txt"
    subprocess.run(
        ["age-keygen", "--output", str(key)], check=True, capture_output=True
    )
    public = subprocess.run(
        ["age-keygen", "-y", str(key)], check=True, capture_output=True, text=True
    )
    return key, public.stdout.strip()


def test_offsite_copy_decrypts_to_the_backup(tmp_path, identity):
    key, recipient = identity
    backup = tmp_path / "radar-2026-10-29-031500.dump"
    backup.write_bytes(b"dump")

    copy = refresh_offsite(tmp_path / "offsite", backup, recipient)

    assert copy.name == "radar-offsite.dump.age"
    assert b"dump" not in copy.read_bytes()
    decrypted = subprocess.run(
        ["age", "--decrypt", "--identity", str(key), str(copy)],
        check=True,
        capture_output=True,
    )
    assert decrypted.stdout == b"dump"
    assert [p.name for p in copy.parent.iterdir()] == [copy.name]


def test_failed_encryption_keeps_the_previous_offsite_copy(tmp_path, identity):
    backup = tmp_path / "radar-2026-10-29-031500.dump"
    backup.write_bytes(b"dump")
    offsite = tmp_path / "offsite"
    offsite.mkdir()
    (offsite / "radar-offsite.dump.age").write_text("previous")

    with pytest.raises(subprocess.CalledProcessError):
        refresh_offsite(offsite, backup, "age1notakey")

    assert [p.name for p in offsite.iterdir()] == ["radar-offsite.dump.age"]
    assert (offsite / "radar-offsite.dump.age").read_text() == "previous"


class FakeClock:
    """Time that moves only when the code under test sleeps."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_waits_until_the_database_is_ready():
    answers = iter([False, False, True])
    clock = FakeClock()

    wait_for_db(lambda: next(answers), timeout=300, sleep=clock.sleep, clock=clock.time)

    assert clock.sleeps == [5, 5]


def test_gives_up_when_the_database_never_starts():
    clock = FakeClock()

    with pytest.raises(TimeoutError):
        wait_for_db(lambda: False, timeout=12, sleep=clock.sleep, clock=clock.time)

    assert clock.sleeps == [5, 5, 5]
