import disnake
from utils import bot, normalize_url
from config import GUILD_IDS, MOD_LOG


class InfoVideoView(disnake.ui.View):
    def __init__(self, ctx, video_info, bot):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.video_info = video_info
        self.bot = bot

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        message = await self.ctx.original_message()
        await message.edit(view=self)

    @disnake.ui.button(label="Delete", style=disnake.ButtonStyle.red, custom_id="delete_video", row=0)
    async def delete_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        button.disabled = True
        self.children[1].disabled = False
        self.children[2].disabled = False
        await interaction.response.edit_message(content="Are you sure you want to delete this video?", view=self)

    @disnake.ui.button(label="Confirm Deletion", style=disnake.ButtonStyle.green, custom_id="confirm_deletion", row=1, disabled=True)
    async def confirm_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        removed_url, removed_name = await self.bot.video_manager.remove_video(self.video_info['name'], "name", MOD_LOG, interaction.user)
        if removed_url:
            content = f"Deleted `{removed_name}` from the database."
        else:
            content = "Error deleting the video. Please try again."
        await interaction.response.edit_message(content=content, view=None)
        self.stop()

    @disnake.ui.button(label="Cancel", style=disnake.ButtonStyle.grey, custom_id="cancel_deletion", row=1, disabled=True)
    async def cancel_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.children[0].disabled = False
        self.children[1].disabled = True
        button.disabled = True
        await interaction.response.edit_message(content="Deletion cancelled.", view=self)


def setup(bot):
    @bot.slash_command(
        name="getinfo",
        description="Find the name and colour of a video in the database by its original URL.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option("url", "The original URL of the video to find.",
                           type=disnake.OptionType.string, required=True)
        ]
    )
    async def findvid(ctx, url: str):
        normalized_url = normalize_url(url)

        video_info = await bot.video_manager.fetch_video_info(normalized_url)
        if video_info is None:
            await ctx.response.send_message("No video found with the given original URL.", ephemeral=True)
            return

        embed = create_embed(video_info)
        view = InfoVideoView(ctx, video_info, bot)
        await ctx.response.send_message(embed=embed, view=view)


def create_embed(video_info):
    color_map = {
        "yellow": 0xFFFF00,
        "red": 0xFF0000,
        "green": 0x00FF00
    }
    color_name = video_info['color'].lower()
    hex_color = color_map.get(color_name, 0x000000)

    added_by = video_info['added_by'].split(
        '#')[0] if '#' in video_info['added_by'] else video_info['added_by']

    hashtags = video_info.get('hashtags', '')
    formatted_hashtags = ', '.join([f'#{tag.strip()}' for tag in hashtags.split(
        ',') if tag.strip()]) if hashtags else 'None'

    hof_status = "🏆" if video_info.get('is_hall_of_fame') else "None"

    embed_description = f"**Name:** `{video_info['name']}`\n**Colour:** `{video_info['color']}`\n**Added by:** `{added_by}`\n**HOF Status:** `{hof_status}`"

    if formatted_hashtags:
        embed_description += f"\n**Hashtags:** `{formatted_hashtags}`"
    else:
        embed_description += "\n**Hashtags:** `None`"

    if 'date_added' in video_info and video_info['date_added']:
        date_added = video_info['date_added']
        embed_description += f"\n**Date added:** `{date_added}`"

    embed = disnake.Embed(
        description=embed_description,
        color=hex_color
    )

    if video_info.get('tiktok_original_link'):
        tiktok_value = f"[Author]({video_info['tiktok_author_link']})\n[Original URL]({video_info['tiktok_original_link']})\n[Sound URL]({video_info['tiktok_sound_link']})"
        embed.add_field(
            name="TikTok", value=tiktok_value, inline=False)

    if video_info.get('insta_original_link'):
        insta_value = f"[Original URL]({video_info['insta_original_link']})"
        embed.add_field(name="Instagram",
                        value=insta_value, inline=False)

    misc_value = f"[Discord backup URL]({video_info['original_url']})"
    embed.add_field(name="Misc.", value=misc_value, inline=False)

    return embed
