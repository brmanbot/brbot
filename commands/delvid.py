import disnake
from utils import has_role_check, bot
from config import GUILD_IDS

video_manager = None

@bot.slash_command(
    name="delvid",
    description="Delete a video with the given name or URL from the database.",
    guild_ids=GUILD_IDS,
    options=[
        disnake.Option(name="identifier", description="The name or URL of the video to delete.", type=disnake.OptionType.string, required=True),
    ]
)
async def delvid(inter, identifier: str):
    global video_manager
    if not await has_role_check(inter):
        await inter.response.send_message("You do not have the required role to run this command.", ephemeral=True)
        return

    identifier_type = "url" if identifier.startswith("https://tinyurl.com/") else "name"
    removed_url, removed_name = await video_manager.remove_video(identifier, identifier_type)

    if removed_url is not None and removed_name is not None:
        await inter.response.send_message(f"Deleted `{removed_name}` from the database.")
    else:
        await inter.response.send_message(f"Failed to delete `{identifier}`: Video not found in the database.", ephemeral=True)
