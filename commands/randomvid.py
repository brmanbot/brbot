import disnake
from utils import bot, fisher_yates_shuffle
from config import COOLDOWN, GUILD_IDS
import time

video_manager = None

@bot.slash_command(
    name="randomvid",
    description="Retrieve a random video from a random or specific colour database.",
    guild_ids=GUILD_IDS,
    options=[
        disnake.Option("colour", "The colour database to search for videos.", type=disnake.OptionType.string, required=False, choices=[
            disnake.OptionChoice("Green", "green"),
            disnake.OptionChoice("Red", "red"),
            disnake.OptionChoice("Yellow", "yellow")
        ])
    ]
)
async def randomvid(ctx, colour: str = None):
    await ctx.response.defer()

    global video_manager
    played_videos = video_manager.played_videos
    current_time = time.time()

    if colour is None:
        available_videos = await video_manager.get_available_videos(["green", "red", "yellow"])
    else:
        available_videos = await video_manager.get_available_videos([colour])

    if not available_videos:
        if colour is None:
            await ctx.followup.send("All videos have been played. Contact brman to fix.")
        else:
            await ctx.followup.send(f"No {colour} videos found in the database.")
        return

    chosen_video = None
    while available_videos:
        fisher_yates_shuffle(available_videos)
        candidate_video = available_videos.pop()

        played_time = played_videos.get(candidate_video, 0)
        if current_time - played_time > COOLDOWN:
            chosen_video = candidate_video
            break

    if not chosen_video:
        await ctx.followup.send("No videos found that meet the cooldown requirement.")
        return

    await ctx.edit_original_message(content=f"{chosen_video}")

    played_videos[chosen_video] = current_time
    video_manager.save_data()
