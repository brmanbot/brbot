import asyncio
import disnake
from utils import bot
from config import GUILD_IDS
import time

def setup(bot):
    @bot.slash_command(
        name="randomvid",
        description="Retrieve a random video from a random or specific colour database.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option("colour", "The colour database to search for videos.", type=disnake.OptionType.string, required=False, choices=[
                disnake.OptionChoice("All", "all"),
                disnake.OptionChoice("Green", "green"),
                disnake.OptionChoice("Red", "red"),
                disnake.OptionChoice("Yellow", "yellow")            
            ])
        ]
    )
    async def randomvid(ctx, colour: str = "yellow"):
        assert bot.video_manager is not None, "video_manager is not initialized"

        await ctx.response.defer()

        played_videos = bot.video_manager.played_videos
        current_time = time.time()

        if colour == "all":
            colours = ["green", "red", "yellow"]
        else:
            colours = [colour]

        available_videos = await bot.video_manager.get_available_videos_with_cooldown(colours, current_time, bot.cooldown)

        if not available_videos:
            await ctx.followup.send("No videos found that meet the cooldown requirement.")
            return

        chosen_video = available_videos[0]

        if chosen_video in bot.video_manager.hall_of_fame:
            chosen_video = "🏆 " + chosen_video

        await ctx.edit_original_message(content=f"{chosen_video}")
        played_videos[chosen_video] = current_time
        bot.video_manager.save_data()