import aiosqlite
import time
from utils import bot, fisher_yates_shuffle
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
    played_videos = video_manager.played_videos
    current_time = time.time()

    available_videos = await video_manager.get_available_videos(["green", "red"])

    if not available_videos:
        await ctx.followup.send("All green and red videos have been played. Contact brman to fix.")
        return

    chosen_video = None
    while available_videos:
        fisher_yates_shuffle(available_videos)
        candidate_video = available_videos.pop()

        played_time = played_videos.get(candidate_video, 0)
        if current_time - played_time > bot.cooldown:
            chosen_video = candidate_video
            break

    if not chosen_video:
        await ctx.followup.send("No videos found that meet the cooldown requirement.", ephemeral=True)
        return

    video_lists = video_manager.video_lists
    selected_color = [c for c in ["green", "red"] if chosen_video in video_lists[c]][0]
    video_lists[selected_color].remove(chosen_video)

    await ctx.edit_original_message(content=f"{chosen_video}")

    played_videos[chosen_video] = current_time
    video_manager.save_data()
