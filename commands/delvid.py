import asyncio
import aiosqlite
import disnake
from utils import bot, has_role_check
from config import GUILD_IDS


class DeleteVideoView(disnake.ui.View):
    def __init__(self, ctx, matched_videos, identifier):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.matched_videos = matched_videos
        self.identifier = identifier
        self.url = matched_videos[0]['url'] if len(matched_videos) == 1 else None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        message = await self.ctx.original_message()
        await message.edit(view=self)

    @disnake.ui.button(label="Delete", style=disnake.ButtonStyle.red, custom_id="delete_video", row=0)
    async def delete_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.delete_button.disabled = True
        self.no_button.disabled = False
        self.confirm_button.disabled = False
        matched_videos_list = "\n".join(f"`{video['name']}`" for video in self.matched_videos)
        await interaction.response.edit_message(content=f"The identifier `{self.identifier}` matched the following {len(self.matched_videos)} videos:\n\n{matched_videos_list}\n\nAre you sure you want to delete these videos?", view=self)

    @disnake.ui.button(label="No", style=disnake.ButtonStyle.grey, custom_id="no_deletion", row=0)
    async def no_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.delete_button.disabled = True
        self.confirm_button.disabled = True
        self.no_button.disabled = True
        await interaction.response.edit_message(content="Cancelled video deletion.", view=self)
        await asyncio.sleep(2)
        await interaction.message.delete()

    @disnake.ui.button(label="Confirm Deletion", style=disnake.ButtonStyle.green, custom_id="confirm_deletion", row=1, disabled=True)
    async def confirm_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        if len(self.matched_videos) > 1:
            deleted_videos = []
            for video in self.matched_videos:
                removed_url, removed_name = await self.ctx.bot.video_manager.remove_video(video['url'], "url") 
                if removed_url and removed_name:
                    deleted_videos.append(removed_name)

            if deleted_videos:
                deleted_videos_string = "\n".join(f"`{name}`" for name in deleted_videos)
                await interaction.response.edit_message(content=f"Deleted the following videos from the database:\n{deleted_videos_string}", view=None)
            else:
                await interaction.response.edit_message(content="Error deleting the videos. Please try again.", view=None)
        else:
            removed_url, removed_name = await self.ctx.bot.video_manager.remove_video(self.url, "url")
            if removed_url and removed_name:
                await interaction.response.edit_message(content=f"Deleted `{removed_name}` from the database.", view=None)
            else:
                await interaction.response.edit_message(content="Error deleting the video. Please try again.", view=None)

def setup(bot):
    @bot.slash_command(
        name="delvid",
        description="Delete a video with the given name or URL from the database.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option("identifier", "The identifier (name or URL) of the video to delete.", type=disnake.OptionType.string, required=True)
        ]
    )
    async def delvid(ctx, identifier: str):
        if not await has_role_check(ctx):
            await ctx.send("You do not have permission to use this command.", ephemeral=True)
            return

        async with aiosqlite.connect("videos.db") as db:
            query = "SELECT name, url FROM videos WHERE name = ? OR url = ?"
            values = (identifier, identifier)
            async with db.execute(query, values) as cursor:
                exact_match = await cursor.fetchone()

        if exact_match:
            name, url = exact_match
            removed_url, removed_name = await ctx.bot.video_manager.remove_video(url, "url")  # updated here
            if removed_url and removed_name:
                await ctx.response.send_message(f"Deleted `{removed_name}` from the database.")
            else:
                await ctx.response.send_message("Error deleting the video. Please try again.")
        else:
            async with aiosqlite.connect("videos.db") as db:
                query = "SELECT name, url FROM videos WHERE name LIKE ? OR url = ?"
                values = (f"%{identifier}%", identifier)
                async with db.execute(query, values) as cursor:
                    matched_videos = await cursor.fetchall()

            if matched_videos is None or len(matched_videos) == 0:
                await ctx.response.send_message("No video found with the given identifier.", ephemeral=True)
            else:
                matched_videos_list = "\n".join(f"`{video[0]}`" for video in matched_videos)
                view = DeleteVideoView(ctx, [{'name': video[0], 'url': video[1]} for video in matched_videos], identifier)
                await ctx.response.send_message(f"The identifier `{identifier}` matched the following `{len(matched_videos)}` videos:\n\n{matched_videos_list}\n\nDo you want to delete them all?", view=view)