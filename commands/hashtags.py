import math
import disnake
from disnake.ext import commands
from utils import fetch_all_hashtags
from config import GUILD_IDS
import uuid


class ListHashtags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="hashtags",
        description="List all unique hashtags in the database.",
        guild_ids=GUILD_IDS
    )
    async def list_hashtags(self, inter: disnake.ApplicationCommandInteraction):
        hashtags = await fetch_all_hashtags()
        if hashtags:
            embed, total_pages = await self.create_hashtags_embed(hashtags, 1)
            view = HashtagPaginator(inter, hashtags, total_pages)
            await inter.response.send_message(embed=embed, view=view)
        else:
            await inter.response.send_message("No hashtags found in the database.", ephemeral=True)

    async def create_hashtags_embed(self, hashtags, page, items_per_page=25):
        total_pages = math.ceil(len(hashtags) / items_per_page)
        page = max(1, min(page, total_pages))

        hashtags_list = '\n'.join(
            hashtags[(page - 1) * items_per_page: page * items_per_page])
        embed = disnake.Embed(
            title=f"Hashtags",
            description=hashtags_list,
            color=disnake.Color.blue()
        )
        embed.set_footer(text=f"Page {page} of {total_pages}")

        return embed, total_pages


class HashtagPaginator(disnake.ui.View):
    def __init__(self, inter, hashtags, total_pages):
        super().__init__()
        self.inter = inter
        self.hashtags = hashtags
        self.page = 1
        self.total_pages = total_pages
        self.add_buttons()

    def add_buttons(self):
        self.previous_button = disnake.ui.Button(
            label="Previous",
            style=disnake.ButtonStyle.secondary,
            custom_id=f"previous_page_{uuid.uuid4()}",
            disabled=self.page <= 1
        )
        self.previous_button.callback = self.previous_page
        self.add_item(self.previous_button)

        self.next_button = disnake.ui.Button(
            label="Next",
            style=disnake.ButtonStyle.secondary,
            custom_id=f"next_page_{uuid.uuid4()}",
            disabled=self.page >= self.total_pages
        )
        self.next_button.callback = self.next_page
        self.add_item(self.next_button)

    async def previous_page(self, interaction: disnake.Interaction):
        if self.page > 1:
            self.page -= 1
            self.update_buttons()
            await interaction.response.defer()
            await self.update_embed(interaction)

    async def next_page(self, interaction: disnake.Interaction):
        if self.page < self.total_pages:
            self.page += 1
            self.update_buttons()
            await interaction.response.defer()
            await self.update_embed(interaction)

    def update_buttons(self):
        self.previous_button.disabled = self.page <= 1
        self.next_button.disabled = self.page >= self.total_pages

    async def update_embed(self, interaction: disnake.Interaction):
        embed, _ = await ListHashtags(self.inter.bot).create_hashtags_embed(self.hashtags, self.page)
        await interaction.edit_original_message(embed=embed, view=self)


def setup(bot):
    bot.add_cog(ListHashtags(bot))
