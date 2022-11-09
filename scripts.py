import argparse
from datetime import date

from telegram.database import PgDatabase
from telegram.scripts import activity_over_time, export, inactive_users


def parse_args():
    # Top level parser
    parser = argparse.ArgumentParser(
        description="Analysis of collected Telegram data (chats, messages, and media)"
    )
    subparsers = parser.add_subparsers(dest="commands")

    # Parser options for activity_over_time
    parser_aot = subparsers.add_parser(
        "activity-over-time",
        help="plots activity over time for collected data",
    )
    parser_aot.add_argument(
        "--dialog-id",
        type=int,
        help="specify dialog to analyze. If not provided, all dialogs will be analyzed",
    )
    parser_aot.add_argument(
        "--min-date",
        type=date.fromisoformat,
        default=date(2020, 1, 1),
        help="lower bound of date interval to analyze (YYYY-MM-DD)",
    )
    parser_aot.add_argument(
        "--max-date",
        type=date.fromisoformat,
        default=date.today(),
        help="upper bound of date interval to analyze (YYYY-MM-DD)",
    )

    # Parser options for inactive_users
    parser_iu = subparsers.add_parser(
        "inactive-users",
        help="finds percentage of users in a chat that have sent less than n messages",
    )
    parser_iu.add_argument(
        "--dialog-id",
        type=int,
        required=True,
        help="specify dialog to analyze",
    )
    parser_iu.add_argument(
        "--min-messages",
        type=int,
        default=3,
        help="minumum number of messages to consider a user active",
    )

    # Parser options for export
    parser_ex = subparsers.add_parser("export", help="export postgres database as file")
    parser_ex.add_argument(
        "--dest-file",
        type=str,
        default="backup.sql",
        help="destination file for exported database",
    )
    parser_ex.add_argument(
        "--compress", action="store_true", help="compress destination file"
    )

    return parser.parse_args()


def main():
    """
    The main telegram-bot analysis program. Runs several small scripts that
    provide useful insights in collected data.
    """
    args = parse_args()
    db = PgDatabase()

    match args.commands:
        case "activity-over-time":
            activity_over_time(args, db)
        case "inactive-users":
            inactive_users(args, db)
        case "export":
            export(args)


if __name__ == "__main__":
    main()
