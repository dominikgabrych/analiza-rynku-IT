"""The `radar` command."""

import argparse

from radar import backup, migrate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radar")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "backup", help="dump the database to BACKUP_DIR and keep the newest copies"
    )
    commands.add_parser(
        "migrate", help="back up the database, then apply pending migrations"
    )
    args = parser.parse_args(argv)
    if args.command == "backup":
        return backup.run()
    if args.command == "migrate":
        return migrate.run()
    return 1
