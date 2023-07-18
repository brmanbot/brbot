import aiosqlite
import disnake
from utils import bot
from config import GUILD_IDS

def setup(bot):
    @bot.slash_command(
        name="totalvids",
        description="Show the total amount of videos in the database for each colour.",
        guild_ids=GUILD_IDS
    )
    async def totalvids(ctx):
        embed = await create_total_videos_embed()
        await ctx.response.send_message(embed=embed)


    async def create_total_videos_embed():
        db = await aiosqlite.connect("videos.db")
        try:
            colors = ["green", "red", "yellow"]
            color_counts = {}
            for color in colors:
                query = "SELECT COUNT(*) FROM videos WHERE LOWER(color) = ?"
                values = (color,)
                async with db.execute(query, values) as cursor:
                    color_counts[color] = (await cursor.fetchone())[0]

            total_videos = sum(color_counts.values())

            embed = disnake.Embed(
                title=f"Total videos in the database ({total_videos})",
                color=disnake.Color.blurple()
            )

            for color, count in color_counts.items():
                embed.add_field(name=f"{color.capitalize()} videos", value=f"{count}", inline=True)

            return embed
        finally:
            await db.close()
