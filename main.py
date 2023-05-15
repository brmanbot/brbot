import asyncio
import disnake
from disnake.ext import commands

from config import ALLOWED_USER_ID, BOSSMANROLE_ID, BOT_TOKEN, INTENTS
from utils import VideoManager, autocomp_colours, bot, load_setup_data, schedule_role_removals, setup_data
from database import initialize_database

import importlib
import pkgutil

command_modules = [importlib.import_module(f'commands.{name}') for _, name, _ in pkgutil.iter_modules(['commands'])]

video_manager = VideoManager()
video_manager.load_data()

for module in command_modules:
    module.video_manager = video_manager

async def setup_reaction_handler_on_restart():
    for guild in bot.guilds:
        message_id, channel_id, target_channel_id = load_setup_data(guild.id)
        if message_id != 0 and target_channel_id != 0:
            try:
                channel = await bot.fetch_channel(channel_id)
                message_with_reactions = await channel.fetch_message(message_id)
                target_channel = await bot.fetch_channel(target_channel_id)
            except disnake.NotFound:
                continue

@bot.event
async def on_ready():
    print(f"Bot is ready as {bot.user}!")
    await setup_reaction_handler_on_restart()
    await schedule_role_removals(bot)

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