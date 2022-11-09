import gzip
import subprocess
from typing import List

from telethon.tl import types

from .common import logger


def print_dialogs(dialogs: List[types.Dialog]) -> None:
    for i, dialog in enumerate(dialogs):
        print(f"[{i+1}] {dialog.title} (id={dialog.id})")


def backup_postgres_db(
    host: str, name: str, port: int, user: str, password: str, dest_file: str
):
    """
    Backup postgres db to a file.
    """
    try:
        process = subprocess.Popen(
            [
                "pg_dump",
                "--dbname=postgresql://{}:{}@{}:{}/{}".format(
                    user, password, host, port, name
                ),
                "-f",
                dest_file,
            ],
            stdout=subprocess.PIPE,
        )
        output = process.communicate()[0]
        if process.returncode != 0:
            logger.error(f"Command failed. Return code : {process.returncode}")
            exit(1)
        return output
    except Exception as e:
        logger.error(e)
        exit(1)


def compress_file(src_file: str):
    compressed_file = f"{src_file}.gz"
    with open(src_file, "rb") as f_in:
        with gzip.open(compressed_file, "wb") as f_out:
            for line in f_in:
                f_out.write(line)
    return compressed_file
