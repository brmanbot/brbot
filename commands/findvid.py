import aiosqlite
import disnake
from utils import bot
from config import GUILD_IDS


@bot.slash_command(
    name="findvid",
    description="Find the name and colour of a video in the database by its URL.",
    guild_ids=GUILD_IDS,
    options=[
        disnake.Option("url", "The URL of the video to find.", type=disnake.OptionType.string, required=True)
    ]
)
async def findvid(ctx, url: str):
    async with aiosqlite.connect("videos.db") as db:
        query = "SELECT name, color FROM videos WHERE url = ? OR original_url = ?"
        values = (url, url)
        async with db.execute(query, values) as cursor:
            result = await cursor.fetchone()

        if result is None:
            await ctx.response.send_message("No video found with the given URL.")
        else:
            name, colour = result
            await ctx.response.send_message(f"`{name}` found in the `{colour}` database with the matching URL.")
