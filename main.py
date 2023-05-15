import disnake
import asyncio
from disnake.ext import commands

from config import ALLOWED_USER_ID, BOSSMANROLE_ID, BOT_TOKEN, INTENTS
from utils import VideoManager, autocomp_colours, bot, load_setup_data, schedule_role_removals, setup_data
from commands import __all__ as commands_list
from database import initialize_database


video_manager = VideoManager()
video_manager.load_data()

import commands.randomvid as randomvid_module
import commands.myreaction as myreaction_module
import commands.findvid as findvid_module
import commands.delvid as delvid_module
import commands.changevidcolour as changevidcolour_module
import commands.setupreactions as setupreactions_module

changevidcolour_module.video_manager = video_manager
randomvid_module.video_manager = video_manager
myreaction_module.video_manager = video_manager
findvid_module.video_manager = video_manager
delvid_module.video_manager = video_manager
setupreactions_module.video_manager = video_manager

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