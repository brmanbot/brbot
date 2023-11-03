import random
import disnake
from disnake import ButtonStyle
from config import GUILD_IDS
from video_manager import VideoManager

class HallOfFameSelector(disnake.ui.View):
    def __init__(self, ctx, videos):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.videos = [[i, url] for i, url in enumerate(videos)]
        self.current_video = 0
        self.previous_video = None

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
        while True:
            self.previous_video = self.current_video
            self.current_video = random.randint(0, len(self.videos) - 1)
            if self.previous_video != self.current_video:
                break
        await self.update_video(interaction)

    async def update_video(self, interaction):
        video_url = self.videos[self.current_video][1]

        if self.current_video == 0:
            self.previous_button.disabled = True
        else:
            self.previous_button.disabled = False

        if self.current_video >= len(self.videos) - 1:
            self.next_button.disabled = True
        else:
            self.next_button.disabled = False

        for idx, component in enumerate(self.children):
            if component.custom_id == "previous_video":
                self.children[idx] = self.previous_button
            elif component.custom_id == "next_video":
                self.children[idx] = self.next_button

        await interaction.response.edit_message(content=video_url, view=self)

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

        view = HallOfFameSelector(ctx, videos)
        await ctx.response.send_message(videos[0], view=view)