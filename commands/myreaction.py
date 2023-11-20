import time
from utils import bot
from config import GUILD_IDS
from disnake.ext import commands
from disnake import Option, OptionType

def setup(bot):
    @bot.slash_command(
        name="myreaction",
        description=("Retrieve a random video from a specified or random "
                     "green or red colour database."),
        guild_ids=GUILD_IDS,
        options=[
            Option(
                name="colour",
                description="Choose between Green (good) or Red (bad)",
                type=OptionType.string,
                required=False,
                choices=["Green", "Red"]
            )
        ]
    )
    async def myreaction(ctx, colour: str = None):
        await ctx.response.defer()

        assert bot.video_manager is not None, \
            "video_manager is not initialized"

        current_time = time.time()

        colour = colour.lower() if colour else None

        color_choices = ["green", "red"] if colour is None else [colour]

        available_videos = await bot.video_manager.get_available_videos_with_cooldown(
            color_choices, current_time, bot.cooldown
        )

        if not available_videos:
            await ctx.followup.send(
                "No available videos for the chosen color or all are under cooldown. "
                "Contact brman to fix."
            )
            return

        chosen_video = available_videos[0]
        bot.video_manager.played_videos[chosen_video] = current_time

        if chosen_video in bot.video_manager.hall_of_fame:
            chosen_video = "🏆 " + chosen_video

        await ctx.edit_original_message(content=f"{chosen_video}")
        bot.video_manager.save_data()