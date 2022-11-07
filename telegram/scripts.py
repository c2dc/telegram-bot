from datetime import date

import matplotlib.pyplot as plt
import pandas as pd

from .database import Database


def activity_over_time(
    db: Database, min_date=date(2020, 1, 1), max_date=date.today()
) -> None:
    df = pd.DataFrame(db.get_all_messages())

    # Select relevant columns and set index
    df = df[["id", "message_utc"]]
    df.set_index("id", inplace=True)

    # Filter data by date
    df = df.loc[
        (df["message_utc"].dt.date >= min_date)
        & (df["message_utc"].dt.date <= max_date)
    ]

    # Group data by year, month
    df = df.groupby([df["message_utc"].dt.year, df["message_utc"].dt.month]).count()

    # Plot graph
    df.plot(kind="bar")
    plt.show()
