import aiosqlite
import disnake
from disnake import ApplicationCommandInteraction
from utils import bot, autocomp_colours, shorten_url
from database import add_video_to_database
from config import GUILD_IDS

@bot.slash_command(
    name="vid",
    description="Save a video with a given name and URL in a specific colour database.",
    guild_ids=GUILD_IDS,
    options=[
        disnake.Option(
            "colour",
            "Choose the colour of the video category (Green, Red, or Yellow).",
            type=disnake.OptionType.string,
            required=True,
            autocomplete=True
        ),
        disnake.Option(
            "name",
            "The name of the video.",
            type=disnake.OptionType.string,
            required=True
        ),
        disnake.Option(
            "url",
            "Provide the URL of the video to save.",
            type=disnake.OptionType.string,
            required=True
        )
    ]
)
async def vid(inter, colour: str, name: str, url: str):
    from main import video_manager
    valid_colours = ["green", "red", "yellow"]
    if colour.lower() not in valid_colours:
        await inter.send("Invalid colour. Please use `Green`, `Red`, or `Yellow`.", ephemeral=True)
        return
    
    if not (url.startswith("https://cdn.discordapp.com/attachments/") or url.startswith("https://media.discordapp.net/attachments/")):
        await inter.response.send_message("Discord video URLs only loser.", ephemeral=True)
        return
    
    short_url = await shorten_url(url)
    if short_url is None:
        await inter.response.send_message("Error creating short URL", ephemeral=True)
        return

    query = "SELECT * FROM videos WHERE name = ? OR url = ? OR original_url = ?"
    values = (name, short_url, url)

    async with aiosqlite.connect("videos.db") as db:
        try:
            async with db.execute(query, values) as cursor:
                results = await cursor.fetchall()

            for result in results:
                if result[1] == name:
                    await inter.response.send_message(f"An entry with the same name `{name}` already exists in the database. Please use a different name.", ephemeral=True)
                    return
                if result[2] == short_url or result[4] == url:
                    await inter.response.send_message(f"An entry with the same URL `{url}` already exists in the database. Please use a different URL or video.", ephemeral=True)
                    return

            await add_video_to_database(name, short_url, colour.lower(), url)
            video_manager.video_lists[colour.lower()].append(short_url)
            video_manager.save_data()
            await inter.response.send_message(f"Saved `{short_url}` as `{name}` in `{colour}` database")
        except aiosqlite.IntegrityError as e:
            if "NOT NULL constraint failed" in str(e):
                column_name = str(e).split("failed: ")[1]
                await inter.response.send_message(f"An error occurred while saving the video: {e}. Column `{column_name}` has a NULL value.", ephemeral=True)
            else:
                await inter.response.send_message(f"An integrity error occurred while saving the video: {e}", ephemeral=True)
        except aiosqlite.Error as e:
            await inter.response.send_message(f"An error occurred while saving the video: {e}", ephemeral=True)

@vid.autocomplete("colour")
async def vid_autocomplete_colour(inter: ApplicationCommandInteraction, user_input: str):
    return await autocomp_colours(inter, user_input)
