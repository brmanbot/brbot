import disnake
import time
import matplotlib.pyplot as plt
import os
import aiohttp
import matplotlib.patheffects as path_effects
from disnake.ext import commands
from config import GUILD_IDS, get_cooldown, update_cooldown, ALLOWED_USER_ID

IMAGE_PATH = 'cooldown_pie_chart.png'


class CooldownManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
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

    @staticmethod
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

    @commands.slash_command(
        name="showcooldown",
        description="Display the current cooldown and video status with a pie chart.",
        guild_ids=GUILD_IDS
    )
    async def showcooldown(self, ctx):
        await ctx.response.defer()
        cooldown_value = get_cooldown()
        cooldown_for_title = CooldownManagement.format_cooldown_for_title(cooldown_value)

        current_time = time.time()
        on_cooldown = 0

        if self.bot.video_manager is None:
            await ctx.send("Video manager is not initialized.")
            return

        total_videos = len(self.bot.video_manager.played_videos)

        for _, timestamp in self.bot.video_manager.played_videos.items():
            if current_time - timestamp < cooldown_value:
                on_cooldown += 1

        available_videos = total_videos - on_cooldown
        self.create_pie_chart(on_cooldown, available_videos, cooldown_for_title, ctx)

    async def create_pie_chart(self, on_cooldown, available_videos, cooldown_for_title, ctx):
        fig, ax = plt.subplots(figsize=(10, 10))
        fig.patch.set_visible(False)
        ax.axis('off')

        color_labels = ['On Cooldown', 'Available']
        sizes = [on_cooldown, available_videos]
        colors = ['#A40000', '#4E9A06']

        wedges, texts, autotexts = plt.pie(
            sizes, labels=None, autopct='%1.1f%%', colors=colors,
            wedgeprops=dict(width=0.3), pctdistance=0.85,
            textprops={'fontsize': 24, 'color': 'white'}
        )

        plt.setp(autotexts, path_effects=[
            path_effects.withStroke(linewidth=3, foreground='black')
        ])

        plt.legend(
            [f"{label} {size}" for label, size in zip(color_labels, sizes)],
            loc="upper left", bbox_to_anchor=(0, 1), fontsize=14
        )

        plt.subplots_adjust(
            left=0, bottom=0, right=1, top=1, wspace=0, hspace=0
        )
        plt.savefig(IMAGE_PATH, transparent=True)

        await self.upload_pie_chart(IMAGE_PATH, cooldown_for_title, ctx)

    async def upload_pie_chart(self, image_path, cooldown_for_title, ctx):
        async with aiohttp.ClientSession() as session:
            with open(image_path, 'rb') as f:
                async with session.post(
                    'https://0x0.st', data={'file': f}
                ) as resp:
                    if resp.status != 200:
                        await ctx.send('Could not upload the image.')
                        return
                    else:
                        img_url = await resp.text()

        os.remove(image_path)

        embed_title = f"Current Cooldown: {cooldown_for_title}"
        embed = disnake.Embed(title=embed_title, color=disnake.Color.blue())
        embed.set_image(url=img_url)

        await ctx.edit_original_message(embed=embed)

    @commands.slash_command(
        name="updatecooldown",
        description="Update the cooldown.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option(
                "value", 
                "The value to set the cooldown to.", 
                type=disnake.OptionType.integer, 
                required=True
            ),
            disnake.Option(
                "unit", 
                "The unit of time for the cooldown.", 
                type=disnake.OptionType.string, 
                required=True, 
                choices=[
                    disnake.OptionChoice("Days", "days"),
                    disnake.OptionChoice("Hours", "hours"),
                    disnake.OptionChoice("Seconds", "seconds")
                ]
            )
        ]
    )
    async def updatecooldown(self, ctx, value: int, unit: str):
        if ctx.author.id != ALLOWED_USER_ID:
            await ctx.send("You do not have permission to use this command.", ephemeral=True)
            return

        if value < 0:
            await ctx.send("Cooldown value must be positive.")
            return

        value_seconds = self.get_seconds(value, unit)
        update_cooldown(value_seconds)
        await ctx.send(f"Cooldown updated to `{value} {unit}`")

    @staticmethod
    def get_seconds(value, unit):
        if unit == "days":
            return value * 86400
        elif unit == "hours":
            return value * 3600
        else:
            return value

def setup(bot):
    bot.add_cog(CooldownManagement(bot))