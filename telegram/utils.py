from enum import Enum
from typing import Any, List

from telethon.tl import types


class Selections(Enum):
    SEARCH_TWITTER = 1
    SEARCH_TELEGRAM = 2
    DOWNLOAD_MESSAGES = 3


def delete_elements(list_object: List[Any], indices: List[int]) -> None:
    indices = sorted(indices, reverse=True)
    for idx in indices:
        if idx < len(list_object):
            list_object.pop(idx)


def select() -> Selections:
    print("[1] Search twitter for channels/groups")
    print("[2] Search telegram for channels/groups")
    print("[3] Download messages from joined channels/groups")
    selection = input('What would you like to do? (eg: "1", "2")\n')

    return Selections(int(selection))


def select_channels(channels: List[types.Dialog]) -> List[types.Dialog]:
    selected_channels = channels.copy()
    for i, channel in enumerate(channels):
        print(f"[{i+1}] {channel.title}")

    exclude = input('Channels to exclude: (eg: "1 2 3")\n')
    indices = [int(i) - 1 for i in exclude.split()]
    delete_elements(selected_channels, indices)

    return selected_channels


def select_groups(groups: List[types.Dialog]) -> List[types.Dialog]:
    selected_groups = groups.copy()
    for i, group in enumerate(groups):
        print(f"[{i+1}] {group.title}")

    exclude = input('Groups to exclude: (eg: "1 2 3")\n')
    indices = [int(i) - 1 for i in exclude.split()]
    delete_elements(selected_groups, indices)

    return selected_groups
