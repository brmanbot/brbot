import asyncio
import disnake
from disnake.ext import commands

from config import ALLOWED_USER_ID, BOSSMANROLE_ID, BOT_TOKEN, INTENTS, GUILD_IDS
from utils import CustomBot, VideoManager, autocomp_colours, load_setup_data, setup_data
from database import initialize_database, synchronize_cache_with_database

import pkgutil

print("Starting the bot...")

async def setup_video_manager(bot):
    bot.video_manager = await VideoManager.create(bot)

async def setup_reaction_handler_on_restart(bot):
    for guild in bot.guilds:
        message_id, channel_id, target_channel_id = load_setup_data(guild.id)
        if message_id != 0 and target_channel_id != 0:
            try:
                channel = await bot.fetch_channel(channel_id)
                message_with_reactions = await channel.fetch_message(message_id)
                target_channel = await bot.fetch_channel(target_channel_id)
            except disnake.NotFound:
                continue

async def main():
    bot = CustomBot(intents=INTENTS, test_guilds=GUILD_IDS)
    print("Bot created...")
    await initialize_database()
    await setup_video_manager(bot)
    await synchronize_cache_with_database()
    
    for _, name, _ in pkgutil.iter_modules(['commands']):
        bot.load_extension(f'commands.{name}')

    @bot.event
    async def on_ready():
        print(f"Bot is ready as {bot.user}!")
        await setup_reaction_handler_on_restart(bot)
    
    try:
        await bot.start(BOT_TOKEN)
    finally:
        print("Bot is shutting down...")
        await bot.close()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print(f"Bot is shutting down...")
    finally:
        loop.close()