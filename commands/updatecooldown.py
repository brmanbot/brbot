import json
import disnake
import time
import matplotlib.pyplot as plt
import io
import matplotlib.patheffects as pe
from commands.showcooldown import format_cooldown_for_title
from config import GUILD_IDS, ALLOWED_USER_ID, update_cooldown, get_cooldown
from utils import bot

def setup(bot):
    @bot.slash_command(
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
    async def updatecooldown(ctx, value: int, unit: str):
        if ctx.author.id != ALLOWED_USER_ID:
            await ctx.send("You do not have permission to use this command.", ephemeral=True)
            return

        if value < 0:
            await ctx.send("Cooldown value must be positive.")
            return

        if unit == "days":
            value_seconds = value * 86400
        elif unit == "hours":
            value_seconds = value * 3600
        else:
            value_seconds = value

        update_cooldown(value_seconds)
        cooldown_value = get_cooldown()
        current_time = time.time()
        on_cooldown = 0

        with open('video_data.json', 'r') as file:
            video_data = json.load(file)

        all_videos = {video for color_list in video_data['video_lists'].values() for video in color_list}
        total_videos = len(all_videos)

        for video in all_videos:
            last_played = video_data['played_videos'].get(video)
            if last_played and (current_time - last_played < cooldown_value):
                on_cooldown += 1

        available_videos = total_videos - on_cooldown

        fig, ax = plt.subplots(figsize=(10, 10))
        fig.patch.set_visible(False)
        ax.axis('off')

        color_labels = ['On Cooldown', 'Available']
        sizes = [on_cooldown, available_videos]
        colors = ['#A40000', '#4E9A06']

        _, _, autotexts = plt.pie(
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

        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='png', transparent=True)
        img_bytes.seek(0)

        async with bot.http_session.post('https://0x0.st', data={'file': img_bytes}) as resp:
            if resp.status != 200:
                await ctx.send('Could not upload the image.')
                return
            else:
                img_url = await resp.text()

        cooldown_for_title = format_cooldown_for_title(cooldown_value)
        embed_title = f"Cooldown Updated: {cooldown_for_title}"
        embed = disnake.Embed(title=embed_title, color=disnake.Color.blue())
        embed.set_image(url=img_url)

        await ctx.send(embed=embed)