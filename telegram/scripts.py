import matplotlib.pyplot as plt
import pandas as pd

from .common import logger
from .database import Database


def activity_over_time(args, db: Database) -> None:
    df = pd.DataFrame(db.get_all_messages(args.dialog_id))

    # Select relevant columns and set index
    df = df[["id", "message_utc"]]
    df.set_index("id", inplace=True)

    # Filter data by date
    df = df.loc[
        (df["message_utc"].dt.date >= args.min_date)
        & (df["message_utc"].dt.date <= args.max_date)
    ]

    # Group data by year, month
    df = df.groupby([df["message_utc"].dt.year, df["message_utc"].dt.month]).count()

    # Plot graph
    df.plot(kind="bar", figsize=(15, 8.1))
    plt.ylabel("Total de mensagens")
    plt.xlabel("Mês/Ano")
    plt.xticks(rotation=45)
    plt.locator_params(axis="x", nbins=6)
    plt.title("Atividade ao longo do tempo")
    plt.legend().remove()
    plt.savefig("activity_over_time.eps")
    plt.show()


def inactive_users(args, db: Database) -> tuple:
    # Get full dialog
    dialog = db.get_channel_by_id(args.dialog_id)

    # Get user dict with post frequency
    df = pd.DataFrame(db.get_users_message_count(args.dialog_id))
    if df.shape[0] == 0:
        logger.info(f"Couldn't find users for dialog {dialog.name}")
        return ()

    # If a user hasn't posted at least min_messages times, it's inactive
    inactive_users = df[df["count"] < args.min_messages]

    # Express results
    string = (
        f"Dialog {dialog.name} ({dialog.channel_id}) has {inactive_users.shape[0]}"
        f" users that posted less than {args.min_messages} messages. \nThis represents "
        f"{inactive_users.shape[0]/df.shape[0]:.2%} of the users in the dialog."
    )
    print(string)
    return (inactive_users.shape[0], df.shape[0])
