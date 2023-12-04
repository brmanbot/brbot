import aiosqlite
import disnake
import aiohttp
import matplotlib.pyplot as plt
import os
import matplotlib.patheffects as pe
from utils import bot
from config import GUILD_IDS

IMAGE_PATH = 'pie_chart.png'

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
            color_labels = ["green", "red", "yellow"]
            pastel_colors = ['#4E9A06', '#A40000', '#FDBF11']
            color_counts = {}
            for color in color_labels:
                query = "SELECT COUNT(*) FROM videos WHERE LOWER(color) = ?"
                values = (color,)
                async with db.execute(query, values) as cursor:
                    color_counts[color] = (await cursor.fetchone())[0]

            total_videos = sum(color_counts.values())

            fig, ax = plt.subplots(figsize=(10,10))
            fig.patch.set_visible(False)
            ax.axis('off')

            wedges, texts, autotexts = plt.pie(color_counts.values(), labels=None, autopct='%1.1f%%', colors=pastel_colors, wedgeprops=dict(width=0.3), pctdistance=0.85, textprops={'fontsize': 24, 'color': 'white'})

            plt.setp(autotexts, path_effects=[pe.withStroke(linewidth=3, foreground='black')])

            plt.legend([f"{color.capitalize()} {count}" for color, count in color_counts.items()], loc="upper left", bbox_to_anchor=(0,1), fontsize=14)

            plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
            plt.savefig(IMAGE_PATH, transparent=True)

            async with aiohttp.ClientSession() as session:
                with open(IMAGE_PATH, 'rb') as f:
                    async with session.post('https://0x0.st', data={'file': f}) as resp:
                        if resp.status != 200:
                            return await ctx.send('Could not upload the image.')
                        else:
                            img_url = await resp.text()

            os.remove(IMAGE_PATH)

            embed = disnake.Embed(
                title=f"Total videos in the database ({total_videos})",
                color=disnake.Color.blurple()
            )

            embed.set_image(url=img_url)
            
            return embed
        finally:
            await db.close()