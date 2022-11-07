import argparse

from telegram.database import PgDatabase
from telegram.scripts import activity_over_time


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analysis of collected Telegram data (chats, messages, and media)"
    )

    parser.add_argument(
        "--activity-over-time",
        action="store_true",
        help="plots activity over time for a given dialog_id",
    )

    return parser.parse_args()


def main():
    """
    The main telegram-bot analysis program. Runs several small scripts that
    provide useful insights in collected data.
    """
    args = parse_args()
    db = PgDatabase()

    if args.activity_over_time is True:
        activity_over_time(db)


if __name__ == "__main__":
    main()
