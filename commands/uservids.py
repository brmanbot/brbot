import aiosqlite
import disnake
import aiohttp
import matplotlib.pyplot as plt
import os
import matplotlib.patheffects as pe
import matplotlib.colors as mcolors
from collections import defaultdict
from utils import bot
from config import GUILD_IDS

IMAGE_PATH = 'user_pie_chart.png'

def setup(bot):
    @bot.slash_command(
        name="uservids",
        description="Show the total amount of videos added by each user.",
        guild_ids=GUILD_IDS
    )
    async def uservids(ctx):
        embed = await create_user_videos_embed()
        await ctx.response.send_message(embed=embed)


    async def create_user_videos_embed():
        db = await aiosqlite.connect("videos.db")
        try:
            user_counts = defaultdict(int)

            query = "SELECT added_by FROM videos"
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    user = row[0].split('#')[0]
                    user_counts[user] += 1

            total_videos = sum(user_counts.values())

            color_list = list(mcolors.TABLEAU_COLORS.keys())
            
            user_colors = {user: color_list[i % len(color_list)].replace('tab:', '') for i, user in enumerate(user_counts.keys())}

            fig, ax = plt.subplots(figsize=(6,6))
            fig.patch.set_visible(False)
            ax.axis('off')

            wedges, texts, autotexts = plt.pie(
                user_counts.values(),
                labels=None,
                autopct='%1.1f%%',
                colors=[user_colors[user] for user in user_counts.keys()],
                wedgeprops=dict(width=0.3),
                pctdistance=0.85,
                textprops={'fontsize': 12, 'color': 'white'}
            )

            plt.setp(autotexts, path_effects=[pe.withStroke(linewidth=3, foreground='black')])

            plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
            plt.savefig(IMAGE_PATH, transparent=True)

            async with aiohttp.ClientSession() as session:
                with open(IMAGE_PATH, 'rb') as f:
                    form = aiohttp.FormData()
                    form.add_field('reqtype', 'fileupload')
                    form.add_field('userhash', '')
                    form.add_field('fileToUpload', f, filename=IMAGE_PATH, content_type='image/png')
                    async with session.post('https://catbox.moe/user/api.php', data=form) as resp:
                        if resp.status != 200:
                            return await ctx.send('Could not upload the image.')
                        else:
                            img_url = await resp.text()

            os.remove(IMAGE_PATH)

            embed = disnake.Embed(
                title=f"Total videos added by each user ({total_videos})",
                color=disnake.Color.blurple()
            )

            sorted_users = sorted(user_counts.items(), key=lambda item: item[1], reverse=True)
            for user, count in sorted_users:
                embed.add_field(name=f"{user} ({user_colors[user]})", value=f"{count}", inline=False)
            
            embed.set_image(url=img_url)
            
            return embed
        finally:
            await db.close()