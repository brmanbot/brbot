import asyncio
import disnake
from disnake.ext import commands

from config import BOT_TOKEN, INTENTS, GUILD_IDS
from utils import CustomBot, VideoManager, load_setup_data
import pkgutil

print("Starting the bot...")


async def setup_video_manager(bot):
    bot.video_manager = await VideoManager.create(bot)
    await bot.video_manager.load_videos_info()


async def setup_reaction_handler_on_restart(bot):
    for guild in bot.guilds:
        message_id, channel_id, target_channel_id = load_setup_data(guild.id)
        if message_id and target_channel_id:
            try:
                channel = await bot.fetch_channel(channel_id)
                message_with_reactions = await channel.fetch_message(message_id)
                target_channel = await bot.fetch_channel(target_channel_id)
            except disnake.NotFound:
                continue


async def main():
    bot = CustomBot(intents=INTENTS, test_guilds=GUILD_IDS)
    print("Bot created...")

    await setup_video_manager(bot)

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
        print("Bot is shutting down...")
    finally:
        loop.close()
