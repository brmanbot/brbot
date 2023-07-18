import aiosqlite
import disnake
from disnake import ApplicationCommandInteraction
from utils import bot, autocomp_video_names
from config import GUILD_IDS

def setup(bot):
    @bot.slash_command(
        name="getvid",
        description="Retrieve the URL of a saved video by name. Use /vids to see a list of all available videos.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option("name", "The name of the video to retrieve.", type=disnake.OptionType.string, required=True, autocomplete=True)
        ]
    )
    async def getvid(ctx, name: str):
        async with aiosqlite.connect("videos.db") as db:
            async with db.execute("SELECT url, is_hall_of_fame FROM videos WHERE name = ?", (name,)) as cursor:
                result = await cursor.fetchone()

                if result is None:
                    await ctx.response.send_message(f"No video found with name `{name}`", ephemeral=True)
                else:
                    video_url, is_hall_of_fame = result
                    if is_hall_of_fame:
                        video_url = "🏆 " + video_url
                    await ctx.response.send_message(video_url)

    @getvid.autocomplete("name")
    async def getvid_autocomplete(inter: ApplicationCommandInteraction, user_input: str):
        return await autocomp_video_names(inter, user_input)
