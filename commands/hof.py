import random
import disnake
from disnake import ButtonStyle
from config import GUILD_IDS
from utils import format_video_url_with_emoji


class HallOfFameSelector(disnake.ui.View):
    def __init__(self, ctx, videos):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.videos = [[i, video] for i, video in enumerate(videos)]
        self.current_video = 0

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        message = await self.ctx.original_message()
        await message.edit(view=self)

    @disnake.ui.button(label="Back", style=ButtonStyle.primary, emoji="◀️", custom_id="previous_video", row=1, disabled=True)
    async def previous_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.current_video = max(0, self.current_video - 1)
        await self.update_video(interaction)

    @disnake.ui.button(label="Forward", style=ButtonStyle.primary, emoji="▶️", custom_id="next_video", row=1)
    async def next_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.current_video = min(len(self.videos) - 1, self.current_video + 1)
        await self.update_video(interaction)

    @disnake.ui.button(label="Shuffle", style=ButtonStyle.primary, emoji="🔀", custom_id="shuffle_videos", row=1)
    async def shuffle_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.previous_video = self.current_video
        self.current_video = random.randint(0, len(self.videos) - 1)
        while self.previous_video == self.current_video:
            self.current_video = random.randint(0, len(self.videos) - 1)
        await self.update_video(interaction)

    async def update_video(self, interaction):
        video_url = self.videos[self.current_video][1]
        formatted_video_url = format_video_url_with_emoji(
            self.ctx.guild, video_url)

        if self.current_video == 0:
            self.previous_button.disabled = True
        else:
            self.previous_button.disabled = False

        if self.current_video >= len(self.videos) - 1:
            self.next_button.disabled = True
        else:
            self.next_button.disabled = False

        await interaction.response.edit_message(content=formatted_video_url, view=self)


def setup(bot):
    @bot.slash_command(
        name="hof",
        description="Show a video from the hall of fame.",
        guild_ids=GUILD_IDS
    )
    async def hof(ctx):
        video_manager = bot.video_manager
        videos = video_manager.hall_of_fame

        if not videos:
            await ctx.send("There are currently no videos in the hall of fame.")
            return

        formatted_first_video_url = format_video_url_with_emoji(
            ctx.guild, videos[0])
        view = HallOfFameSelector(ctx, videos)
        await ctx.response.send_message(formatted_first_video_url, view=view)
