from typing import Any, List

from telethon.tl import types


def delete_elements(list_object: List[Any], indices: List[int]) -> None:
    indices = sorted(indices, reverse=True)
    for idx in indices:
        if idx < len(list_object):
            list_object.pop(idx)


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
