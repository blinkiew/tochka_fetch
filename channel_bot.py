from dotenv import load_dotenv
from models import TelegramPost
from os import getenv
from telegram import Bot


load_dotenv()
TOKEN = getenv("BOT_TOKEN")
CHANNEL_ID = getenv("CHANNEL_ID")


class TelegramBot:
    def __init__(self):
        self.bot = Bot(token=TOKEN)

    async def send_schedule(self, path: str, post: TelegramPost):
        with open(path, 'rb') as photo_file:
            await self.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo_file,
                caption=post.caption
            )
