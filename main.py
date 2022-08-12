from common import config
from telethon import TelegramClient

client = TelegramClient("anon", config["api_id"], config["api_hash"])


async def main():
    me = await client.get_me()

    print(me.stringify())


with client:
    client.loop.run_until_complete(main())
