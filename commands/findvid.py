import aiosqlite
import disnake
from utils import bot, VideoManager
from config import GUILD_IDS

video_manager = VideoManager()
remove_video = video_manager.remove_video

class DeleteVideoView(disnake.ui.View):
    def __init__(self, ctx, url, name, colour):
        super().__init__()
        self.ctx = ctx
        self.url = url
        self.name = name
        self.colour = colour

    @disnake.ui.button(label="Delete", style=disnake.ButtonStyle.red, custom_id="delete_video", row=0)
    async def delete_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.delete_button.disabled = True
        self.confirm_button.disabled = False
        self.cancel_button.disabled = False
        await interaction.response.edit_message(content="Are you sure you want to delete this video?", view=self)

    @disnake.ui.button(label="Confirm Deletion", style=disnake.ButtonStyle.green, custom_id="confirm_deletion", row=1, disabled=True)
    async def confirm_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        removed_url, removed_name = await remove_video(self.url, "url")
        if removed_url and removed_name:
            await interaction.response.edit_message(content=f"Deleted `{removed_name}` from the database.", view=None)
        else:
            await interaction.response.edit_message(content="Error deleting the video. Please try again.", view=None)

    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.grey, custom_id="cancel_deletion", row=1, disabled=True)
    async def cancel_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.delete_button.disabled = False
        self.confirm_button.disabled = True
        self.cancel_button.disabled = True
        await interaction.response.edit_message(content=f"`{self.name}` found in the `{self.colour}` database with the matching URL.", view=self)

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
            view = DeleteVideoView(ctx, url, name, colour)
            await ctx.response.send_message(f"`{name}` found in the `{colour}` database with the matching URL.", view=view)
