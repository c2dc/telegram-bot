from typing import List

from telethon.tl import types


def print_dialogs(dialogs: List[types.Dialog]) -> None:
    for i, dialog in enumerate(dialogs):
        print(f"[{i+1}] {dialog.title} (id={dialog.id})")
