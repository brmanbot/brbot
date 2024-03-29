import disnake
from utils import autocomp_colours, autocomp_video_names
from config import GUILD_IDS
from disnake import ApplicationCommandInteraction


def setup(bot):
    @bot.slash_command(
        name="changevidcolour",
        description="Change the colour of a video in the database.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option("name", "The name of the video to change colour.",
                           type=disnake.OptionType.string, required=True, autocomplete=True),
            disnake.Option("colour", "The new colour for the video (Green, Red, or Yellow).",
                           type=disnake.OptionType.string, required=True, autocomplete=True)
        ]
    )
    async def changevidcolour(inter: disnake.ApplicationCommandInteraction, name: str, colour: str):
        valid_colours = ["green", "red", "yellow"]
        if colour.lower() not in valid_colours:
            await inter.response.send_message("Invalid colour. Please use `Green`, `Red`, or `Yellow`.", ephemeral=True)
            return

        old_colour = await bot.video_manager.get_video_color(name)
        if old_colour is None:
            await inter.response.send_message(f"No video found with name `{name}`", ephemeral=True)
            return

        if old_colour == colour.lower():
            await inter.response.send_message(f"The video `{name}` is already in the `{colour}` database.", ephemeral=True)
            return

        await bot.video_manager.change_video_color(name, colour.lower())
        await bot.video_manager.change_video_color_in_cache(name, colour.lower())

        await inter.response.send_message(f"Moved `{name}` from `{old_colour.capitalize()}` to `{colour.capitalize()}` database.")

    @changevidcolour.autocomplete("colour")
    async def changevidcolour_autocomplete(inter: ApplicationCommandInteraction, user_input: str):
        return await autocomp_colours(inter, user_input)

    @changevidcolour.autocomplete("name")
    async def changevidcolour_autocomplete_name(inter: ApplicationCommandInteraction, user_input: str):
        return await autocomp_video_names(inter, user_input)
