import re
import aiosqlite
import disnake
import aiohttp
import io
from disnake import ApplicationCommandInteraction
from utils import bot, autocomp_colours, shorten_url, has_role_check
from database import add_video_to_database
from config import GUILD_IDS
from private_config import TIKTOK_ARCHIVE_CHANNEL, RAPID_API_KEY

async def fetch_content(session, url, content_type):
    headers = {"User-Agent": "MyBot"}
    if content_type == "tiktok":
        api_url = "https://api.tik.fail/api/grab"
        data = {"url": url}
        response = await session.post(api_url, headers=headers, data=data)
    elif content_type == "instagram":
        api_url = "https://instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com/"
        querystring = {"url": url}
        headers.update({
            "X-RapidAPI-Key": RAPID_API_KEY,
            "X-RapidAPI-Host": "instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com"
        })
        response = await session.get(api_url, headers=headers, params=querystring)

        if response.status == 200:
            data = await response.json()

            if isinstance(data, list) and data and "url" in data[0]:
                return data[0]["url"]
        return None

async def download_video(session, video_url):
    async with session.get(video_url) as response:
        if response.status == 200:
            return io.BytesIO(await response.read())
        else:
            return None

async def video_exists(name, url, db_path="videos.db"):
    query = "SELECT * FROM videos WHERE name = ? OR url = ?"
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(query, (name, url)) as cursor:
            return await cursor.fetchone() is not None

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
                "Provide the URL of the video to save (TikTok, Instagram Reels, or Discord video URL).",
                type=disnake.OptionType.string,
                required=True
            )
        ]
    )
    async def vid(inter, colour: str, name: str, url: str):
        if not await has_role_check(inter):
            await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        await inter.response.send_message("Processing your request...", ephemeral=True)

        tiktok_url_pattern = r'(https?://(vm\.tiktok\.com/[\w-]+)|(https?://www\.tiktok\.com/@[\w-]+/video/[\d]+))'
        tiktok_url = re.match(tiktok_url_pattern, url)
        instagram_url = "instagram.com" in url and re.match(
            r'https?://www\.instagram\.com/([a-zA-Z0-9_.]+/)?(p|reel)/[a-zA-Z0-9-_]+', url)
        discord_url = url.startswith("https://cdn.discordapp.com/attachments/") or url.startswith(
            "https://media.discordapp.net/attachments/")

        async with aiohttp.ClientSession() as session:
            if tiktok_url or instagram_url:
                content_type = "tiktok" if tiktok_url else "instagram"
                content_response = await fetch_content(session, url, content_type)
                if content_response:
                    if content_type == "tiktok" and content_response.get("success"):
                        video_url = content_response["data"]["download"]["video"].get("NoWM", {}).get("url")
                    elif content_type == "instagram":
                        video_url = content_response
                    else:
                        await inter.followup.send(f"Failed to fetch {content_type} content.", ephemeral=True)
                        return

                    video_data = await download_video(session, video_url)
                    if video_data:
                        if await video_exists(name, url):
                            await inter.followup.send("A video with the same name or URL already exists.", ephemeral=True)
                            return

                        upload_channel = bot.get_channel(int(TIKTOK_ARCHIVE_CHANNEL))
                        if upload_channel:
                            video_message = await upload_channel.send(
                                file=disnake.File(fp=video_data, filename=f"{name}.mp4")
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
                                await inter.followup.send("Failed to shorten the URL.", ephemeral=True)
                        else:
                            await inter.followup.send("Invalid upload channel ID.", ephemeral=True)
                    else:
                        await inter.followup.send(f"Failed to download {content_type} video.", ephemeral=True)
                else:
                    await inter.followup.send(f"Failed to fetch {content_type} content.", ephemeral=True)

            elif discord_url:
                if await video_exists(name, url):
                    await inter.followup.send("A video with the same name or URL already exists.", ephemeral=True)
                    return

                short_url = await shorten_url(url)
                if short_url is None:
                    await inter.followup.send("Error creating short URL", ephemeral=True)
                    return

                added_by = f"{inter.user.name}#{inter.user.discriminator}"
                await add_video_to_database(name, short_url, colour.lower(), url, added_by)
                bot.video_manager.video_lists[colour.lower()].append(short_url)
                bot.video_manager.save_data()
                await inter.followup.send(f"Saved `{short_url}` as `{name}` in `{colour}` database")

            else:
                await inter.followup.send(
                    "Invalid URL. Please provide a valid TikTok, Instagram, or Discord video URL.", ephemeral=True)

    @vid.autocomplete("colour")
    async def vid_autocomplete_colour(inter: ApplicationCommandInteraction, user_input: str):
        return await autocomp_colours(inter, user_input)