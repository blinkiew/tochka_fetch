from models import Post
from telegram import Bot


class TelegramAPI:
    def __init__(self, token: str, channel_id: int | str):
        self.bot = Bot(token=token)
        self.channel_id = channel_id

    async def send_schedule(self, post: Post):
        await self.bot.send_photo(
            chat_id=self.channel_id,
            caption=post.caption,
            photo=post.photo
        )

    # TODO: add bot notification integrations
