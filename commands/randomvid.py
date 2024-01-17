import asyncio
import re
import disnake
import time
from utils import bot, has_role_check
from config import MOD_LOG


class ConfirmView(disnake.ui.View):
    def __init__(self, original_view, ctx):
        super().__init__()
        self.original_view = original_view
        self.ctx = ctx

    @disnake.ui.button(style=disnake.ButtonStyle.success, label='Confirm')
    async def confirm_button(self, _, interaction):
        deleted_by_user = interaction.user

        video_info = await self.original_view.bot.video_manager.fetch_video_info(
            self.original_view.video_url)
        if video_info is not None:
            video_name = video_info['name']
            await self.original_view.bot.video_manager.remove_video(
                self.original_view.video_url, 'url', MOD_LOG, deleted_by_user)
            await interaction.response.send_message(
                f"Deleted `{video_name}` from the database.")
            for item in self.original_view.children:
                if item.custom_id in ["delete_video", "info_video"]:
                    item.disabled = True
            self.confirm_button.disabled = True
            await self.original_view.ctx.edit_original_message(view=self.original_view)


class VideoActionsView(disnake.ui.View):
    def __init__(self, ctx, video_url, bot, selected_colors,
                 info_message_id=None, info_message_channel_id=None,
                 start_time=None):
        self.ctx = ctx
        self.video_url = video_url
        self.bot = bot
        self.selected_colors = selected_colors
        self.info_message_id = info_message_id
        self.info_message_channel_id = info_message_channel_id
        self.start_time = start_time if start_time is not None else time.time()

        remaining_time = 180 - (time.time() - self.start_time)

        if remaining_time <= 0:
            super().__init__(timeout=None)
            self.disable_all_buttons()
        else:
            super().__init__(timeout=remaining_time)

    def disable_all_buttons(self):
        for item in self.children:
            item.disabled = True

    async def disable_buttons_after_delay(self, bot, ctx, message_id, delay):
        await asyncio.sleep(delay)
        message = await ctx.channel.fetch_message(message_id)
        view = bot.active_videos.get(message.id)
        if view is not None:
            view.disable_all_buttons()
            await message.edit(view=view)
            del bot.active_videos[message.id]

    @disnake.ui.button(label="Re-roll", style=disnake.ButtonStyle.primary,
                       emoji="🔀", custom_id="reroll_video", row=0)
    async def reroll_button(self, button, interaction):
        button.disabled = True
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
                self.info_message_id, self.info_message_channel_id, time.time())

            for item in view.children:
                if item.custom_id == "info_video":
                    item.disabled = False

            new_message = await interaction.followup.send(content=f"{display_video_url}", view=view)
            self.bot.active_videos[new_message.id] = view

            asyncio.create_task(self.disable_buttons_after_delay(self.bot, self.ctx, new_message.id, view.timeout))

            self.bot.video_manager.save_data()
        else:
            button.disabled = True
            await interaction.followup.send("No available videos to re-roll.", ephemeral=True)

    @disnake.ui.button(label="Info", style=disnake.ButtonStyle.primary, emoji="ℹ️", custom_id="info_video", row=0)
    async def info_button(self, button, interaction):
        await interaction.response.defer()
        video_url = self.video_url
        if video_url.startswith("🏆 "):
            video_url = video_url[2:]
        video_info = await self.bot.video_manager.fetch_video_info(video_url)

        if video_info:
            color_map = {
                "yellow": 0xFFFF00,
                "red": 0xFF0000,
                "green": 0x00FF00
            }
            color_name = video_info['color'].lower()
            hex_color = color_map.get(color_name, 0x000000)

            added_by = video_info['added_by'].split('#')[0] if '#' in video_info['added_by'] else video_info['added_by']
            date_added = video_info.get('date_added', "before 15/01/2024")

            embed = disnake.Embed(
                description=f"**Name:** `{video_info['name']}`\n**Colour:** `{video_info['color']}`\n**Added by:** `{added_by}`",
                color=hex_color
            )

            if video_info.get('tiktok_original_link'):
                tiktok_value = (
                    f"[TikTok original URL]({video_info['tiktok_original_link']})\n"
                    f"[Author]({video_info['tiktok_author_link']})\n\n"
                    f"[TikTok sound URL]({video_info['tiktok_sound_link']})"
                )
                video_id_match = re.findall(r'video/(\d+)', video_info['tiktok_original_link'])
                if video_id_match:
                    video_id = video_id_match[0]
                    tiktok_value += f"\n[TikTok sound download](https://www.tikwm.com/video/media/play/{video_id}.mp4)"
                embed.add_field(name="TikTok", value=tiktok_value, inline=True)

            if video_info.get('insta_original_link'):
                insta_value = f"[Instagram URL]({video_info['insta_original_link']})"
                embed.add_field(name="Instagram", value=insta_value, inline=True)

            misc_value = f"[Shortened URL]({video_info['url']})\n[Discord backup URL]({video_info['original_url']})"
            embed.add_field(name="Misc.", value=misc_value, inline=True)

            embed.set_footer(text=f"Date added: {date_added}")

            info_message = await interaction.followup.send(embed=embed)

            if info_message is not None:
                self.info_message_channel_id = info_message.channel.id
                self.info_message_id = info_message.id

            button.disabled = True
            await interaction.message.edit(view=self)
        else:
            await interaction.followup.send("Video not found in database.")

    @disnake.ui.button(label="Delete", style=disnake.ButtonStyle.danger, emoji="🗑️",
                       custom_id="delete_video", row=0)
    async def delete_button(self, button, interaction):
        if not await has_role_check(interaction):
            await interaction.response.send_message("You don't have the permissions to delete this video.", ephemeral=True)
            return

        video_url = self.video_url
        if video_url.startswith("🏆 "):
            video_url = video_url[2:]
        video_info = await self.bot.video_manager.fetch_video_info(video_url)
        if video_info is not None:
            video_name = video_info['name']
            confirm_view = ConfirmView(self, self.ctx)
            confirm_message = await interaction.response.send_message("Are you sure you want to delete this video?", view=confirm_view, ephemeral=True)
            confirm_view.message = confirm_message
        else:
            await interaction.response.send_message(f"Video not found in database.")


def setup(bot):
    @bot.slash_command(
        name="randomvid",
        description="Retrieve a random video from a random or specific colour database.",
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
    async def randomvid(ctx, colour: str = "all"):
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
        message = await ctx.edit_original_message(content=f"{display_video}", view=view)
        bot.active_videos[message.id] = view

        asyncio.create_task(view.disable_buttons_after_delay(bot, ctx, message.id, view.timeout))
        
        bot.video_manager.save_data()