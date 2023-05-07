import aiosqlite
import time
from utils import bot, fisher_yates_shuffle, VideoManager
from config import COOLDOWN, GUILD_IDS

video_manager = VideoManager()
played_videos = video_manager.played_videos
get_available_videos = video_manager.get_available_videos
video_lists = video_manager.video_lists


@bot.slash_command(
    name="myreaction",
    description="Retrieve a random video from a random green or red colour database.",
    guild_ids=GUILD_IDS,
)
async def myreaction(ctx):
    await ctx.response.defer()

    global played_videos

    current_time = time.time()

    available_videos = await get_available_videos(["green", "red"])

    if not available_videos:
        await ctx.followup.send("All green and red videos have been played. Contact brman to fix.")
        return

    all_played_recently = True
    while all_played_recently:
        fisher_yates_shuffle(available_videos)
        chosen_video = available_videos.pop()

        played_time = played_videos.get(chosen_video, 0)
        if current_time - played_time > COOLDOWN:
            all_played_recently = False
        else:
            if not available_videos:
                for c in ["green", "red"]:
                    query = "SELECT url FROM videos WHERE color = ?"
                    values = (c,)
                    async with aiosqlite.connect("videos.db") as db:
                        async with db.execute(query, values) as cursor:
                            results = await cursor.fetchall()

                    video_lists[c] = [url for url, in results]
                    fisher_yates_shuffle(video_lists[c])
                    available_videos.extend(video_lists[c])

    selected_color = [c for c in ["green", "red"] if chosen_video in video_lists[c]][0]
    video_lists[selected_color].remove(chosen_video)

    await ctx.edit_original_message(content=f"{chosen_video}")

    played_videos[chosen_video] = current_time
    video_manager.save_data()
