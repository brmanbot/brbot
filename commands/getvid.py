import aiosqlite
import disnake
from disnake import ApplicationCommandInteraction
from utils import bot, autocomp_video_names
from config import GUILD_IDS


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
        async with db.execute("SELECT url FROM videos WHERE name = ?", (name,)) as cursor:
            result = await cursor.fetchone()

            if result is None:
                await ctx.response.send_message(f"No video found with name `{name}`", ephemeral=True)
            else:
                await ctx.response.send_message(result[0])


@getvid.autocomplete("name")
async def getvid_autocomplete(inter: ApplicationCommandInteraction, user_input: str):
    return await autocomp_video_names(inter, user_input)
