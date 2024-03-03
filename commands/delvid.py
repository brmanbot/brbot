import asyncio
import aiosqlite
import disnake
from utils import bot, has_role_check, normalize_url
from config import GUILD_IDS, MOD_LOG


class DeleteVideoView(disnake.ui.View):
    def __init__(self, ctx, matched_videos, identifier):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.matched_videos = matched_videos
        self.identifier = identifier
        self.original_url = matched_videos[0]['original_url'] if len(
            matched_videos) == 1 else None

        if matched_videos:
            self.confirm_button.disabled = False

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        message = await self.ctx.original_message()
        await message.edit(view=self)

    @disnake.ui.button(label="Confirm Deletion", style=disnake.ButtonStyle.green, custom_id="confirm_deletion", row=1, disabled=True)
    async def confirm_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):

        if len(self.matched_videos) > 1:
            deleted_videos = []
            for video in self.matched_videos:
                removed_url, removed_name = await self.ctx.bot.video_manager.remove_video(video['original_url'], "original_url", MOD_LOG, interaction.user)
                if removed_url:
                    await self.ctx.bot.video_manager.remove_video_from_cache(removed_name.lower())
                    deleted_videos.append(removed_name)

            if deleted_videos:
                deleted_videos_string = "\n".join(deleted_videos)
                await interaction.response.edit_message(content=f"Deleted the following videos from the database:\n`{deleted_videos_string}`", view=None)
            else:
                await interaction.response.edit_message(content="Error deleting the videos. Please try again.", view=None)
        else:
            removed_url, removed_name = await self.ctx.bot.video_manager.remove_video(self.original_url, "original_url", MOD_LOG, interaction.user)
            if removed_url:
                await self.ctx.bot.video_manager.remove_video_from_cache(removed_name.lower())
                await interaction.response.edit_message(content=f"Deleted `{removed_name}` from the database.", view=None)
            else:
                await interaction.response.edit_message(content="Error deleting the video. Please try again.", view=None)


def setup(bot):
    @bot.slash_command(
        name="delvid",
        description="Delete a video with the given name or original URL from the database.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option("identifier", "The identifier (name or original URL) of the video to delete.",
                           type=disnake.OptionType.string, required=True)
        ]
    )
    async def delvid(ctx, identifier: str):
        if not await has_role_check(ctx):
            await ctx.send("You do not have permission to use this command.", ephemeral=True)
            return

        normalized_identifier = normalize_url(identifier)

        async with aiosqlite.connect("videos.db") as db:
            query = "SELECT name, original_url FROM videos WHERE name = ? OR original_url LIKE ?"
            values = (identifier, normalized_identifier)
            async with db.execute(query, values) as cursor:
                exact_match = await cursor.fetchone()

        if exact_match:
            name, original_url = exact_match
            removed_url, removed_name = await ctx.bot.video_manager.remove_video(original_url, "original_url", MOD_LOG, ctx.author)
            await ctx.bot.video_manager.remove_video_from_cache(removed_name.lower())
            if removed_url:
                await ctx.response.send_message(f"Deleted `{removed_name}` from the database.")
            else:
                await ctx.response.send_message("Error deleting the video. Please try again.")
        else:
            async with aiosqlite.connect("videos.db") as db:
                query = "SELECT name, original_url FROM videos WHERE name LIKE ? OR original_url LIKE ?"
                values = (f"%{identifier}%", f"%{identifier}%")
                async with db.execute(query, values) as cursor:
                    matched_videos = await cursor.fetchall()

            if not matched_videos:
                await ctx.response.send_message("No video found with the given identifier.", ephemeral=True)
            else:
                video_names = [video[0] for video in matched_videos]

                video_names_str = "\n".join(video_names)
                message = (f"The identifier `{identifier}` matched the following `{len(matched_videos)}` videos. "
                           f"Do you want to delete them all?\n\n`{video_names_str}`")

                view = DeleteVideoView(
                    ctx, [{'name': video[0], 'original_url': video[1]} for video in matched_videos], identifier)

                await ctx.response.send_message(message, view=view)
