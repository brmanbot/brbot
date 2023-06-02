import time
from utils import bot
from config import GUILD_IDS

video_manager = None

@bot.slash_command(
    name="myreaction",
    description="Retrieve a random video from a random green or red colour database.",
    guild_ids=GUILD_IDS,
)
async def myreaction(ctx):
    await ctx.response.defer()

    global video_manager
    current_time = time.time()

    available_videos = await video_manager.get_available_videos_with_cooldown(["green", "red"], current_time, bot.cooldown)

    if not available_videos:
        await ctx.followup.send("All green and red videos have been played or are under cooldown. Contact brman to fix.")
        return

    chosen_video = available_videos[0]

    await ctx.edit_original_message(content=f"{chosen_video}")

    video_manager.played_videos[chosen_video] = current_time
    video_manager.save_data()
