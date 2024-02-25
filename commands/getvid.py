import aiosqlite
import disnake
from disnake import ApplicationCommandInteraction, OptionChoice
from utils import bot, autocomp_video_names, fetch_videos_by_name_or_hashtag
from config import GUILD_IDS


def setup(bot):
    @bot.slash_command(
        name="getvid",
        description="Retrieve the URL of a saved video by name. Use /vids to see a list of all available videos.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option(
                "identifier",
                "The name or related hashtag of the video to retrieve.",
                type=disnake.OptionType.string,
                required=True,
                autocomplete=True
            )
        ]
    )
    async def getvid(ctx: ApplicationCommandInteraction, identifier: str):
        video_name = identifier.strip()

        async with aiosqlite.connect("videos.db") as db:
            query = "SELECT name, original_url, is_hall_of_fame FROM videos WHERE LOWER(name) = LOWER(?)"
            async with db.execute(query, (video_name,)) as cursor:
                video = await cursor.fetchone()

        if video:
            name, original_url, is_hall_of_fame = video
            hof_icon = "🏆 " if is_hall_of_fame else ""
            await ctx.response.send_message(f"{hof_icon}[{name}]({original_url})")
        else:
            await ctx.response.send_message(f"No video found with the name '{video_name}'.", ephemeral=True)

    @getvid.autocomplete("identifier")
    async def getvid_autocomplete(inter: ApplicationCommandInteraction, user_input: str):
        return await autocomp_video_names(inter, user_input)
