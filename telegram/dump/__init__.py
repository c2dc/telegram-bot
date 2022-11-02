from ..client import TelegramClient
from ..database import Database
from ..utils import select_dialogs
from .dialog import download_dialogs
from .media import download_media


class Dumper:
    def __init__(self, client: TelegramClient, db: Database) -> None:
        self.client = client
        self.db = db

    async def download_dialogs(self) -> None:
        dialogs = await self.client.get_dialogs()
        selected_dialogs = select_dialogs(dialogs)

        return await download_dialogs(
            client=self.client, db=self.db, dialogs=selected_dialogs
        )

    async def download_past_media(self, dialog_id: int) -> None:
        dialogs = []
        if dialog_id != 0:
            dialog = await self.client.get_entity_from_id(dialog_id)
            if dialog:
                dialogs.append(dialog)
        else:
            dialogs = await self.client.get_dialogs()

        return await download_media(client=self.client, db=self.db, dialogs=dialogs)
