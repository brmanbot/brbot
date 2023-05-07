import math
import aiosqlite
import disnake
from disnake import ButtonStyle
from utils import bot
from config import GUILD_IDS

@bot.slash_command(
    name="vids",
    description="List all videos for each colour database.",
    guild_ids=GUILD_IDS
)
async def vids(ctx):
    embed = await create_embed("green", 1)
    view = ColourSelector(ctx)
    await ctx.response.send_message(embed=embed, view=view)

async def create_embed(colour, page, items_per_page=30):
    db = await aiosqlite.connect("videos.db")
    try:
        query = "SELECT name, url FROM videos WHERE color = ?"
        values = (colour,)
        async with db.execute(query, values) as cursor:
            videos = await cursor.fetchall()

        total_pages = math.ceil(len(videos) / items_per_page)
        page = max(1, min(page, total_pages))

        video_links = '\n'.join(
            [f"[{video[0]}]({video[1]})" for video in videos[(page - 1) * items_per_page: page * items_per_page]])

        embed = disnake.Embed(
            title=f"{colour.capitalize()} videos ({len(videos)})",
            description=video_links,
            color=disnake.Color.green() if colour == "green" else (
                disnake.Color.red() if colour == "red" else disnake.Color.gold())
        )
        embed.set_footer(text=f"Page {page} of {total_pages}")

        return embed
    finally:
        await db.close()

class ColourSelector(disnake.ui.View):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.page = 1
        self.colour = "green"

    @disnake.ui.button(label="Green", style=ButtonStyle.green, custom_id="green_vids", row=0)
    async def green_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.colour = "green"
        self.page = 1
        await self.update_embed(interaction)

    @disnake.ui.button(label="Red", style=ButtonStyle.red, custom_id="red_vids", row=0)
    async def red_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.colour = "red"
        self.page = 1
        await self.update_embed(interaction)

    @disnake.ui.button(label="Yellow", style=ButtonStyle.blurple, custom_id="yellow_vids", row=0)
    async def yellow_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.colour = "yellow"
        self.page = 1
        await self.update_embed(interaction)

    @disnake.ui.button(label="Previous", style=ButtonStyle.secondary, custom_id="previous_page", row=1, disabled=True)
    async def previous_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.page = max(1, self.page - 1)
        await self.update_embed(interaction)

    @disnake.ui.button(label="Next", style=ButtonStyle.secondary, custom_id="next_page", row=1)
    async def next_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        self.page += 1
        await self.update_embed(interaction)

    @disnake.ui.button(label="Last Page", style=ButtonStyle.secondary, custom_id="last_page", row=1)
    async def last_page_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        embed = await create_embed(self.colour, self.page)
        total_pages = int(embed.footer.text.split()[-1])
        self.page = total_pages
        await self.update_embed(interaction)

    async def update_embed(self, interaction):
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

        await interaction.response.edit_message(embed=embed, view=self)

