import disnake
from utils import bot, autocomp_colours, autocomp_video_names
from config import GUILD_IDS
from disnake import ApplicationCommandInteraction

video_manager = None

@bot.slash_command(
    name="changevidcolour",
    description="Change the colour of a video in the database.",
    guild_ids=GUILD_IDS,
    options=[
        disnake.Option("identifier", "The name or URL of the video to change colour.", type=disnake.OptionType.string, required=True, autocomplete=True),
        disnake.Option("colour", "The new colour for the video (green, red, or yellow).", type=disnake.OptionType.string, required=True, autocomplete=True)
    ]
)
async def changevidcolour(inter: disnake.ApplicationCommandInteraction, identifier: str, colour: str):
    valid_colours = ["green", "red", "yellow"]
    if colour.lower() not in valid_colours:
        await inter.response.send_message("Invalid colour. Please use `green`, `red`, or `yellow`.")
        return

    identifier_type = "url" if identifier.startswith("https://tinyurl.com/") else "name"
    old_colour = await video_manager.get_video_color(identifier, identifier_type)
    if old_colour is None:
        await inter.response.send_message(f"No video found with identifier `{identifier}`")
        return

    if old_colour == colour:
        await inter.response.send_message(f"The video `{identifier}` is already in the `{colour}` database.")
        return

    await video_manager.change_video_color(identifier, identifier_type, colour)
    await inter.response.send_message(f"Moved `{identifier}` from `{old_colour}` to `{colour}` database.")


@changevidcolour.autocomplete("colour")
async def changevidcolour_autocomplete(inter: ApplicationCommandInteraction, user_input: str):
    return await autocomp_colours(inter, user_input)


@changevidcolour.autocomplete("identifier")
async def changevidcolour_autocomplete_identifier(inter: ApplicationCommandInteraction, user_input: str):
    return await autocomp_video_names(inter, user_input)