import disnake
import time
import matplotlib.pyplot as plt
import os
import aiohttp
import matplotlib.patheffects as pe
from config import GUILD_IDS, get_cooldown
from utils import bot

IMAGE_PATH = 'cooldown_pie_chart.png'


def format_cooldown(cooldown_value):
    days, remainder = divmod(cooldown_value, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    formatted_cooldown = []
    if days:
        formatted_cooldown.append(f"{days} days")
    if hours:
        formatted_cooldown.append(f"{hours} hours")
    if minutes:
        formatted_cooldown.append(f"{minutes} minutes")
    if seconds or not formatted_cooldown:
        formatted_cooldown.append(f"{seconds} seconds")

    return ", ".join(formatted_cooldown)


def format_cooldown_for_title(cooldown_value):
    days, remainder = divmod(cooldown_value, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days}d"
    elif hours > 0:
        return f"{hours}h"
    elif minutes > 0:
        return f"{minutes}m"
    else:
        return f"{seconds}s"


def setup(bot):
    @bot.slash_command(
        name="showcooldown",
        description="Display the current cooldown and video status with a pie chart.",
        guild_ids=GUILD_IDS,
    )
    async def showcooldown(ctx):
        await ctx.response.defer()
        cooldown_value = get_cooldown()
        cooldown_for_title = format_cooldown_for_title(cooldown_value)

        current_time = time.time()
        on_cooldown = 0
        total_videos = len(bot.video_manager.played_videos)

        for _, timestamp in bot.video_manager.played_videos.items():
            if current_time - timestamp < cooldown_value:
                on_cooldown += 1

        available_videos = total_videos - on_cooldown

        fig, ax = plt.subplots(figsize=(10, 10))
        fig.patch.set_visible(False)
        ax.axis('off')

        color_labels = ['On Cooldown', 'Available']
        sizes = [on_cooldown, available_videos]
        colors = ['#A40000', '#4E9A06']

        wedges, texts, autotexts = plt.pie(
            sizes,
            labels=None,
            autopct='%1.1f%%',
            colors=colors,
            wedgeprops=dict(width=0.3),
            pctdistance=0.85,
            textprops={'fontsize': 24, 'color': 'white'}
        )

        plt.setp(
            autotexts,
            path_effects=[pe.withStroke(linewidth=3, foreground='black')]
        )

        plt.legend(
            [f"{label} {size}" for label, size in zip(color_labels, sizes)],
            loc="upper left",
            bbox_to_anchor=(0, 1),
            fontsize=14
        )

        plt.subplots_adjust(
            left=0, bottom=0, right=1, top=1, wspace=0, hspace=0
        )
        plt.savefig(IMAGE_PATH, transparent=True)

        async with aiohttp.ClientSession() as session:
            with open(IMAGE_PATH, 'rb') as f:
                async with session.post('https://0x0.st', data={'file': f}) as resp:
                    if resp.status != 200:
                        await ctx.send('Could not upload the image.')
                        return
                    else:
                        img_url = await resp.text()

        os.remove(IMAGE_PATH)

        embed_title = f"Current Cooldown: {cooldown_for_title}"
        embed = disnake.Embed(title=embed_title, color=disnake.Color.blue())
        embed.set_image(url=img_url)

        await ctx.edit_original_message(embed=embed)