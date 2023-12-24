import aiosqlite
import disnake
import aiohttp
import io
from disnake import ApplicationCommandInteraction
from utils import bot, autocomp_colours, shorten_url
from database import add_video_to_database
from config import GUILD_IDS
from private_config import TIKTOK_ARCHIVE_CHANNEL


async def resolve_short_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.head(url, allow_redirects=True) as response:
            return str(response.url)


async def fetch_tiktok_content(session, url):
    async with session.post(
        "https://api.tik.fail/api/grab",
        headers={"User-Agent": "MyTikTokBot"},
        data={"url": url}
    ) as response:
        if response.status == 200:
            return await response.json()
        else:
            return None


async def download_video(video_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(video_url) as response:
            if response.status == 200:
                return io.BytesIO(await response.read())
            else:
                return None


def setup(bot):
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
        await inter.send("Processing your request...", ephemeral=True)
        tiktok_url = "tiktok.com" in url

        if tiktok_url:
            resolved_url = await resolve_short_url(url)
            async with aiohttp.ClientSession() as session:
                tiktok_response = await fetch_tiktok_content(session, resolved_url)
                if tiktok_response and tiktok_response.get("success"):
                    video_url = tiktok_response["data"]["download"]["video"].get("NoWM", {}).get("url")
                    tiktok_author = tiktok_response['data']['metadata'].get('AccountProfileName', 'Unknown')
                    original_tiktok_url = tiktok_response['data']['metadata'].get('VideoURL', 'Unknown')
                    video_data = await download_video(video_url)
                    if video_data:
                        upload_channel = bot.get_channel(int(TIKTOK_ARCHIVE_CHANNEL))
                        if upload_channel:
                            try:
                                video_message = await upload_channel.send(
                                    file=disnake.File(fp=video_data, filename="tiktok_video.mp4")
                                )
                                resolved_url = video_message.attachments[0].url
                                short_url = await shorten_url(resolved_url)
                                if short_url:
                                    added_by = f"{inter.user.name}#{inter.user.discriminator}"
                                    await add_video_to_database(name, short_url, colour.lower(), resolved_url, added_by)
                                    bot.video_manager.video_lists[colour.lower()].append(short_url)
                                    bot.video_manager.save_data()
                                    await inter.followup.send(f"Saved `{short_url}` as `{name}` in `{colour}` database")
                                else:
                                    await inter.followup.send("Failed to shorten the URL.")
                                return
                            except Exception as e:
                                await inter.followup.send(f"An error occurred: {e}")
                                return
                        else:
                            await inter.followup.send("Invalid upload channel ID.")
                            return
                    else:
                        await inter.followup.send("Failed to download TikTok video.")
                        return
                else:
                    await inter.followup.send("Failed to fetch TikTok content.")
                    return

        if not tiktok_url:
            if not (url.startswith("https://cdn.discordapp.com/attachments/") or
                    url.startswith("https://media.discordapp.net/attachments/")):
                await inter.followup.send("Discord video URLs only.", ephemeral=True)
                return

            short_url = await shorten_url(url)
            if short_url is None:
                await inter.followup.send("Error creating short URL")
                return

            added_by = f"{inter.user.name}#{inter.user.discriminator}"
            
            query = ("SELECT * FROM videos WHERE name = ? OR url = ? OR original_url = ?")
            values = (name, short_url, url)

            async with aiosqlite.connect("videos.db") as db:
                try:
                    async with db.execute(query, values) as cursor:
                        results = await cursor.fetchall()

                    for result in results:
                        if result[1] == name:
                            await inter.followup.send(
                                f"An entry with the same name `{name}` already exists in the database. "
                                "Please use a different name."
                            )
                            return
                        if result[2] == short_url or result[4] == url:
                            await inter.followup.send(
                                f"An entry with the same URL `{url}` already exists in the database. "
                                "Please use a different URL or video."
                            )
                            return

                    await add_video_to_database(name, short_url, colour.lower(), url, added_by)

                    bot.video_manager.video_lists[colour.lower()].append(short_url)
                    bot.video_manager.save_data()
                    await inter.followup.send(
                        f"Saved `{short_url}` as `{name}` in `{colour}` database"
                    )
                except aiosqlite.IntegrityError as e:
                    if "NOT NULL constraint failed" in str(e):
                        column_name = str(e).split("failed: ")[1]
                        await inter.followup.send(
                            f"An error occurred while saving the video: {e}. Column `{column_name}` has a NULL value."
                        )
                    else:
                        await inter.followup.send(
                            f"An integrity error occurred while saving the video: {e}"
                        )
                except aiosqlite.Error as e:
                    await inter.followup.send(
                        f"An error occurred while saving the video: {e}"
                    )

    @vid.autocomplete("colour")
    async def vid_autocomplete_colour(inter: ApplicationCommandInteraction, user_input: str):
        return await autocomp_colours(inter, user_input)