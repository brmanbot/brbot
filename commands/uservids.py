import aiosqlite
import disnake
import matplotlib.pyplot as plt
import io
import matplotlib.patheffects as pe
import matplotlib.colors as mcolors
from collections import defaultdict
from utils import bot
from config import GUILD_IDS

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
            sorted_users = sorted(
                user_counts.items(), key=lambda item: item[1], reverse=True
            )

            color_list = list(mcolors.TABLEAU_COLORS.keys())
            user_colors = {
                user: color_list[i % len(color_list)].replace('tab:', '') 
                for i, (user, _) in enumerate(sorted_users)
            }

            fig, ax = plt.subplots(figsize=(10, 10))
            fig.patch.set_visible(False)
            ax.axis('off')

            wedges, texts, autotexts = plt.pie(
                [count for _, count in sorted_users],
                labels=None,
                autopct='%1.1f%%',
                colors=[user_colors[user] for user, _ in sorted_users],
                wedgeprops=dict(width=0.3),
                pctdistance=0.85,
                textprops={'fontsize': 24, 'color': 'white'}
            )

            plt.setp(
                autotexts, 
                path_effects=[pe.withStroke(linewidth=3, foreground='black')]
            )
            plt.legend(
                [f"{user} {count}" for user, count in sorted_users],
                loc="upper left",
                bbox_to_anchor=(0, 1),
                fontsize=14
            )

            plt.subplots_adjust(
                left=0, bottom=0, right=1, top=1, wspace=0, hspace=0
            )

            img_bytes = io.BytesIO()
            plt.savefig(img_bytes, format='png', transparent=True)
            img_bytes.seek(0)

            async with bot.http_session.post('https://0x0.st', data={'file': img_bytes}) as resp:
                if resp.status != 200:
                    return await ctx.send('Could not upload the image.')
                else:
                    img_url = await resp.text()

            embed = disnake.Embed(
                title=f"Total videos added by each user ({total_videos})",
                color=disnake.Color.blurple()
            )
            embed.set_image(url=img_url)
            
            return embed
        finally:
            await db.close()