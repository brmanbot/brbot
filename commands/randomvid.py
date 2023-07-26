import disnake
import time
from commands.findvid import DeleteVideoView
from utils import bot, has_role_check
from config import GUILD_IDS


class ConfirmView(disnake.ui.View):
    def __init__(self, original_view):
        super().__init__()
        self.original_view = original_view

    @disnake.ui.button(style=disnake.ButtonStyle.success, label='Confirm')
    async def confirm_button(self, _, interaction: disnake.Interaction):
        video_info = await self.original_view.bot.video_manager.fetch_video_info(self.original_view.video_url)
        if video_info is not None:
            video_name, _, _ = video_info
            await self.original_view.bot.video_manager.remove_video(self.original_view.video_url, 'url')
            await interaction.response.send_message(f"Deleted `{video_name}` from the database.")
            await self.original_view.ctx.edit_original_message(view=self.original_view)


class VideoActionsView(disnake.ui.View):
    def __init__(self, ctx, video_url, bot, selected_colors,
                 info_message_id=None, info_message_channel_id=None):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.video_url = video_url
        self.bot = bot
        self.selected_colors = selected_colors
        self.info_message_id = info_message_id
        self.info_message_channel_id = info_message_channel_id

    async def on_timeout(self):
        message = await self.ctx.original_message()
        await message.edit(view=self)
        if self.info_message_id is not None:
            channel = self.bot.get_channel(self.info_message_channel_id)
            info_message = await channel.fetch_message(self.info_message_id)
            await info_message.delete()

    @disnake.ui.button(label="Re-roll", style=disnake.ButtonStyle.primary,
                    emoji="🔀", custom_id="reroll_video", row=0)
    async def reroll_button(self, button: disnake.ui.Button,
                            interaction: disnake.Interaction):
        await interaction.response.edit_message(view=self)

        current_time = time.time()
        available_videos = await self.bot.video_manager.get_available_videos_with_cooldown(
            self.selected_colors, current_time, self.bot.cooldown)
        if available_videos:
            new_video_url = available_videos[0]
            self.bot.video_manager.played_videos[new_video_url] = current_time
            display_video_url = "🏆 " + new_video_url if new_video_url in self.bot.video_manager.hall_of_fame else new_video_url
            view = VideoActionsView(
                self.ctx, display_video_url, self.bot, self.selected_colors,
                self.info_message_id, self.info_message_channel_id)

            await interaction.followup.send(content=f"{display_video_url}", view=view)

            self.bot.video_manager.save_data()
        else:
            await interaction.followup.send("No available videos to re-roll.", ephemeral=True)

    @disnake.ui.button(label="Info", style=disnake.ButtonStyle.primary,
                        emoji="ℹ️", custom_id="info_video", row=0)
    async def info_button(self, button: disnake.ui.Button,
                        interaction: disnake.Interaction):
        await interaction.response.defer()
        video_url = self.video_url
        if video_url.startswith("🏆 "):
            video_url = video_url[2:]
        result = await self.bot.video_manager.fetch_video_info(video_url)
        if result is not None:
            name, colour, added_by = result
            username = added_by.split('#')[0]
            info_message_content = (
                f"`{name}` found in the `{colour}` database with the matching URL, added by `{username}`.")

            if self.info_message_id is not None:
                channel = self.bot.get_channel(self.info_message_channel_id)
                info_message = await channel.fetch_message(self.info_message_id)
                await info_message.delete()

            info_message = await self.ctx.send(info_message_content)

            if info_message is not None:
                self.info_message_channel_id = info_message.channel.id
                self.info_message_id = info_message.id

            await interaction.message.edit(view=self)

    @disnake.ui.button(label="Delete", style=disnake.ButtonStyle.primary, emoji="🗑️", custom_id="delete_video", row=0)
    async def delete_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        if not await has_role_check(interaction):
            await interaction.response.send_message("You don't have the permissions to delete this video.", ephemeral=True)
            return

        video_url = self.video_url
        if video_url.startswith("🏆 "):
            video_url = video_url[2:]
        video_info = await self.bot.video_manager.fetch_video_info(video_url)
        if video_info is not None:
            video_name, _, _ = video_info
            confirm_view = ConfirmView(self)
            confirm_message = await interaction.response.send_message("Are you sure you want to delete this video?", view=confirm_view, ephemeral=True)
            confirm_view.message = confirm_message
        else:
            await interaction.response.send_message(f"Video not found in database.")


def setup(bot):
    @bot.slash_command(
        name="randomvid",
        description="Retrieve a random video from a random or specific colour database.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option("colour", "The colour database to search for videos.",
                           type=disnake.OptionType.string, required=False,
                           choices=[
                               disnake.OptionChoice("All", "all"),
                               disnake.OptionChoice("Green", "green"),
                               disnake.OptionChoice("Red", "red"),
                               disnake.OptionChoice("Yellow", "yellow")
                           ])
        ]
    )
    async def randomvid(ctx, colour: str = "yellow"):
        assert bot.video_manager is not None, "video_manager is not initialized"

        await ctx.response.defer()

        played_videos = bot.video_manager.played_videos
        current_time = time.time()

        if colour == "all":
            colours = ["green", "red", "yellow"]
        else:
            colours = [colour]

        available_videos = await bot.video_manager.get_available_videos_with_cooldown(
            colours, current_time, bot.cooldown)

        if not available_videos:
            await ctx.followup.send("No videos found that meet the cooldown requirement.")
            return

        chosen_video = available_videos[0]
        bot.video_manager.played_videos[chosen_video] = current_time

        display_video = "🏆 " + chosen_video if chosen_video in bot.video_manager.hall_of_fame else chosen_video

        view = VideoActionsView(ctx, display_video, bot, colours)
        await ctx.edit_original_message(content=f"{display_video}", view=view)
        bot.video_manager.save_data()