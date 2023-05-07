import disnake
from disnake.ext import commands
from utils import has_role_check, VideoManager, bot
from config import GUILD_IDS

video_manager = VideoManager()


@bot.slash_command(
    name="delvid",
    description="Delete a video with the given name from the database.",
    guild_ids=GUILD_IDS,
    options=[
        disnake.Option("name", "The name of the video to delete.", type=disnake.OptionType.string, required=True)
    ]
)
async def delvid(inter, name: str):
    if not await has_role_check(inter):
        await inter.response.send_message("You do not have the required role to run this command.")
        return

    removed_url = await video_manager.remove_video(name)

    if removed_url is not None:
        await inter.response.send_message(f"Deleted `{name}` from the database.")
    else:
        await inter.response.send_message(f"Failed to delete `{name}`: video not found in the database.")
