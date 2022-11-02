from typing import Any, List

from telethon.tl import types


def delete_elements(list_object: List[Any], indices: List[int]) -> None:
    indices = sorted(indices, reverse=True)
    for idx in indices:
        if idx < len(list_object):
            list_object.pop(idx)


def select_dialogs(dialogs: List[types.Dialog]) -> List[types.Dialog]:
    selected_dialogs = dialogs.copy()
    for i, dialog in enumerate(dialogs):
        print(f"[{i+1}] {dialog.title}")

    exclude = input('Dialogs to exclude: (eg: "1 2 3")\n')
    indices = [int(i) - 1 for i in exclude.split()]
    delete_elements(selected_dialogs, indices)

    return selected_dialogs
