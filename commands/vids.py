import math
import aiosqlite
import disnake
from disnake import ButtonStyle
from utils import bot
from config import GUILD_IDS


def setup(bot):
    @bot.slash_command(
        name="vids",
        description="List all videos for each colour database.",
        guild_ids=GUILD_IDS
    )
    async def vids(ctx):
        colour = "green"
        embed = await create_embed(colour, 1)
        view = ColourSelector(ctx, colour)
        await ctx.response.send_message(embed=embed, view=view)

    async def fetch_videos(colour):
        async with aiosqlite.connect("videos.db") as db:
            query = "SELECT name, original_url FROM videos WHERE LOWER(color) = LOWER(?)"
            values = (colour,)
            async with db.execute(query, values) as cursor:
                videos = await cursor.fetchall()
        return videos

    async def create_embed(colour, page, items_per_page=30):
        videos = await fetch_videos(colour)
        video_links = ''
        total_pages = math.ceil(len(videos) / items_per_page)
        page = max(1, min(page, total_pages))

        while items_per_page > 0:
            start_index = (page - 1) * items_per_page
            end_index = start_index + items_per_page
            video_links = '\n'.join(
                [f"[{video[0]}]({video[1]})" for video in videos[start_index:end_index]])

            if len(video_links) <= 4096:
                break
            items_per_page -= 1

        embed = disnake.Embed(
            title=f"{colour.capitalize()} videos ({len(videos)})",
            description=video_links,
            color=disnake.Color.green() if colour == "green" else (
                disnake.Color.red() if colour == "red" else disnake.Color.gold())
        )
        embed.set_footer(
            text=f"Page {page} of {math.ceil(len(videos) / max(items_per_page, 1))}")

        return embed

    class ColourSelector(disnake.ui.View):
        def __init__(self, ctx, colour):
            super().__init__(timeout=180)
            self.ctx = ctx
            self.page = 1
            self.colour = colour

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True
            message = await self.ctx.original_message()
            await message.edit(view=self)

        async def defer_and_update_embed(self, interaction):
            await interaction.response.defer()
            embed = await create_embed(self.colour, self.page)

            if self.page == 1:
                self.previous_button.disabled = True
            else:
                self.previous_button.disabled = False

            total_pages = int(embed.footer.text.split()[-1])
            if self.page >= total_pages:
                self.next_button.disabled = True
                self.last_page_button.disabled = True
            else:
                self.next_button.disabled = False
                self.last_page_button.disabled = False

            for idx, component in enumerate(self.children):
                if component.custom_id == "previous_page":
                    self.children[idx] = self.previous_button
                elif component.custom_id == "next_page":
                    self.children[idx] = self.next_button
                elif component.custom_id == "last_page":
                    self.children[idx] = self.last_page_button

            await interaction.edit_original_message(embed=embed, view=self)

        @disnake.ui.button(label="Green", style=ButtonStyle.green, custom_id="green_vids", row=0)
        async def green_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
            self.colour = "green"
            self.page = 1
            await self.defer_and_update_embed(interaction)

        @disnake.ui.button(label="Red", style=ButtonStyle.red, custom_id="red_vids", row=0)
        async def red_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
            self.colour = "red"
            self.page = 1
            await self.defer_and_update_embed(interaction)

        @disnake.ui.button(label="Yellow", style=ButtonStyle.blurple, custom_id="yellow_vids", row=0)
        async def yellow_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
            self.colour = "yellow"
            self.page = 1
            await self.defer_and_update_embed(interaction)

        @disnake.ui.button(label="Previous", style=ButtonStyle.secondary, custom_id="previous_page", row=1, disabled=True)
        async def previous_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
            self.page = max(1, self.page - 1)
            await self.defer_and_update_embed(interaction)

        @disnake.ui.button(label="Next", style=ButtonStyle.secondary, custom_id="next_page", row=1)
        async def next_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
            self.page += 1
            await self.defer_and_update_embed(interaction)

        @disnake.ui.button(label="Last Page", style=ButtonStyle.secondary, custom_id="last_page", row=1)
        async def last_page_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
            embed = await create_embed(self.colour, self.page)
            total_pages = int(embed.footer.text.split()[-1])
            self.page = total_pages
            await self.defer_and_update_embed(interaction)
