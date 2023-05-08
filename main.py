import disnake
import asyncio
from disnake.ext import commands

from config import ALLOWED_USER_ID, BOSSMANROLE_ID, BOT_TOKEN, INTENTS
from utils import VideoManager, autocomp_colours, bot
from commands import __all__ as commands_list
from database import initialize_database


video_manager = VideoManager()
video_manager.load_data()


@bot.event
async def on_ready():
    print(f"Bot is ready as {bot.user}!")


async def main():
    await initialize_database()

    try:
        await bot.start(BOT_TOKEN)
    except KeyboardInterrupt:
        await bot.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot is shutting down...")
        loop.run_until_complete(bot.close())
        loop.close()
