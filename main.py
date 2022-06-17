import os

from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
client = TelegramClient('anon', api_id, api_hash)

async def main():
    me = await client.get_me()

    print(me.stringify())

with client:
    client.loop.run_until_complete(main())
