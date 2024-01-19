import re
import disnake
from utils import bot
from config import GUILD_IDS, MOD_LOG

class DeleteVideoView(disnake.ui.View):
    def __init__(self, ctx, url, name, colour, bot):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.url = url
        self.name = name
        self.colour = colour
        self.bot = bot

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        message = await self.ctx.original_message()
        await message.edit(view=self)

    @disnake.ui.button(label="Delete", style=disnake.ButtonStyle.red, custom_id="delete_video", row=0)
    async def delete_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.delete_button.disabled = True
        self.confirm_button.disabled = False
        self.cancel_button.disabled = False
        await interaction.response.edit_message(content="Are you sure you want to delete this video?", view=self)

    @disnake.ui.button(label="Confirm Deletion", style=disnake.ButtonStyle.green, custom_id="confirm_deletion", row=1, disabled=True)
    async def confirm_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        removed_url, removed_name = await self.bot.video_manager.remove_video(self.url, "url", MOD_LOG, interaction.user)
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

def setup(bot):
    @bot.slash_command(
        name="getinfo",
        description="Find the name and colour of a video in the database by its URL.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option("url", "The URL of the video to find.", type=disnake.OptionType.string, required=True)
        ]
    )
    async def findvid(ctx, url: str):
        video_info = await bot.video_manager.fetch_video_info(url)
        if video_info is None:
            await ctx.response.send_message("No video found with the given URL.", ephemeral=True)
            return

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
                f"[Author]({video_info['tiktok_author_link']})\n"
                f"[Original URL]({video_info['tiktok_original_link']})\n"
                f"[Sound URL]({video_info['tiktok_sound_link']})\n"
            )
            video_id_match = re.findall(r'video/(\d+)', video_info['tiktok_original_link'])
            if video_id_match:
                video_id = video_id_match[0]
                tiktok_value += f"[Source URL](https://www.tikwm.com/video/media/play/{video_id}.mp4)"
            embed.add_field(name="TikTok", value=tiktok_value, inline=True)

        if video_info.get('insta_original_link'):
            insta_value = f"[Original URL]({video_info['insta_original_link']})"
            embed.add_field(name="Instagram", value=insta_value, inline=True)

        misc_value = f"[Shortened URL]({video_info['url']})\n[Discord backup URL]({video_info['original_url']})"
        embed.add_field(name="Misc.", value=misc_value, inline=True)

        embed.set_footer(text=f"Date added: {date_added}")

        view = DeleteVideoView(ctx, url, video_info['name'], video_info['color'], bot)
        await ctx.response.send_message(embed=embed, view=view)