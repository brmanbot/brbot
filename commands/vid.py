import re
import aiosqlite
import disnake
import io
from datetime import datetime
from disnake import ApplicationCommandInteraction
from utils import bot, autocomp_colours, shorten_url, has_role_check
from database import add_video_to_database
from config import GUILD_IDS
from private_config import TIKTOK_ARCHIVE_CHANNEL, RAPID_API_KEY

async def fetch_content(session, url, content_type):
    headers = {"User-Agent": "MyBot"}
    tiktok_author_link = tiktok_original_link = tiktok_sound_link = None
    if content_type == "tiktok":
        api_url = "https://api.tik.fail/api/grab"
        data = {"url": url}
        response = await session.post(api_url, headers=headers, data=data)
        if response.status == 200:
            data = await response.json()
            if data.get("success"):
                tiktok_author_link = data["data"]["metadata"]["AccountProfileURL"]
                tiktok_original_link = data["data"]["metadata"]["VideoURL"]
                tiktok_sound_link = data["data"]["metadata"]["AudioURL"]
                return data["data"]["download"]["video"].get("NoWM", {}).get("url"), tiktok_author_link, tiktok_original_link, tiktok_sound_link
            else:
                video_id_match = re.search(r'/video/(\d+)', url)
                author_match = re.search(r'https?://www\.tiktok\.com/@([^/]+)/', url)
                if video_id_match and author_match:
                    video_id = video_id_match.group(1)
                    author_username = author_match.group(1)
                    backup_video_url = f"https://www.tikwm.com/video/media/play/{video_id}.mp4"
                    backup_sound_url = f"https://www.tikwm.com/video/music/{video_id}.mp3"
                    tiktok_author_link = f"https://www.tiktok.com/@{author_username}/"
                    backup_response = await session.get(backup_video_url, headers=headers)
                    if backup_response.status == 200:
                        return backup_video_url, tiktok_author_link, url, backup_sound_url
        return None, None, None, None
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
                return data[0]["url"], None, None, None
        return url, None, None, None

    return None, None, None, None

async def download_video(session, video_url):
    async with session.get(video_url) as response:
        if response.status == 200:
            return io.BytesIO(await response.read())
        return None

async def video_exists(name, shortened_url, original_discord_url, tiktok_original_link, insta_original_link, db_path="videos.db"):
    query = """
    SELECT name, url, original_url, tiktok_original_link, insta_original_link 
    FROM videos 
    WHERE name = ? OR url = ? OR original_url = ? OR tiktok_original_link = ? OR insta_original_link = ?
    """
    params = (name, shortened_url, original_discord_url, tiktok_original_link, insta_original_link)
    conflict_details = []
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                video_name, video_url, original_url, tiktok_link, insta_link = row
                if video_name == name:
                    conflict_details.append(("Name", video_url))
                if shortened_url and video_url == shortened_url:
                    conflict_details.append(("Shortened URL", video_url))
                if original_discord_url and original_url == original_discord_url:
                    conflict_details.append(("Discord URL", video_url))
                if tiktok_original_link and tiktok_link == tiktok_original_link:
                    conflict_details.append(("TikTok URL", video_url))
                if insta_original_link and insta_link == insta_original_link:
                    conflict_details.append(("Instagram URL", video_url))
    return conflict_details

async def create_conflict_message(conflict_details, video_manager):
    conflict_messages = []
    for conflict_type, url in conflict_details:
        video_info = await video_manager.fetch_video_info(url)
        if video_info:
            video_name = video_info['name']
            conflict_messages.append(f"{conflict_type}: [{video_name}]({url})")
    return "\n".join(conflict_messages)

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
        short_url = tiktok_original_link = insta_original_link = None

        if not await has_role_check(inter):
            await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        await inter.response.send_message("Processing your request...", ephemeral=True)

        tiktok_url_pattern = r'https?://(vm\.tiktok\.com/\w+|www\.tiktok\.com/@[\w.-]+/video/\d+)'
        tiktok_url = re.match(tiktok_url_pattern, url)
        instagram_url = "instagram.com" in url and re.match(
            r'https?://www\.instagram\.com/([a-zA-Z0-9_.]+/)?(p|reel)/[a-zA-Z0-9-_]+', url)
        discord_url = url.startswith("https://cdn.discordapp.com/attachments/") or url.startswith(
            "https://media.discordapp.net/attachments/")
        date_added = datetime.now().strftime("%d/%m/%Y")

        if tiktok_url or instagram_url:
            content_type = "tiktok" if tiktok_url else "instagram"
            video_url, tiktok_author_link, tiktok_original_link, tiktok_sound_link = await fetch_content(bot.http_session, url, content_type)

            if not video_url:
                await inter.followup.send("Could not fetch the video URL.", ephemeral=True)
                return

            if instagram_url:
                insta_original_link = url
                tiktok_original_link = None
            else:
                insta_original_link = None

            conflict_details = await video_exists(name, short_url, url, tiktok_original_link, insta_original_link)
            conflict_message = await create_conflict_message(conflict_details, bot.video_manager)
            if conflict_message:
                await inter.followup.send(f"Video(s) exist with same information:\n{conflict_message}", ephemeral=True)
                return
                
            video_data = await download_video(bot.http_session, video_url)
            if video_data:
                upload_channel = bot.get_channel(int(TIKTOK_ARCHIVE_CHANNEL))
                if upload_channel:
                    video_message = await upload_channel.send(
                        file=disnake.File(fp=video_data, filename=f"{name}.mp4")
                    )
                    resolved_url = video_message.attachments[0].url
                    short_url = await shorten_url(resolved_url)

                    if short_url:
                        added_by = f"{inter.user.name}#{inter.user.discriminator}"
                        original_url = resolved_url
                        insta_original_link = url if instagram_url else None

                        await add_video_to_database(name, short_url, colour.lower(), original_url, added_by, tiktok_author_link, tiktok_original_link, tiktok_sound_link, insta_original_link, date_added, bot.video_manager)
                        bot.video_manager.video_lists[colour.lower()].append(short_url)
                        bot.video_manager.save_data()
                        await inter.followup.send(f"Saved `{short_url}` as `{name}` in `{colour}` database")
                    else:
                        await inter.followup.send("Failed to shorten the URL.", ephemeral=True)
                else:
                    await inter.followup.send("Invalid upload channel ID.", ephemeral=True)
            else:
                await inter.followup.send("Failed to download video.", ephemeral=True)

        elif discord_url:
            short_url = await shorten_url(url)
            conflict_details = await video_exists(name, short_url, url, tiktok_original_link, insta_original_link)
            conflict_message = await create_conflict_message(conflict_details, bot.video_manager)
            if conflict_message:
                await inter.followup.send(f"Video(s) exist with same information:\n{conflict_message}", ephemeral=True)
                return

            short_url = await shorten_url(url)
            if short_url:
                added_by = f"{inter.user.name}#{inter.user.discriminator}"
                await add_video_to_database(name, short_url, colour.lower(), url, added_by, None, None, None, None, date_added, bot.video_manager)
                bot.video_manager.video_lists[colour.lower()].append(short_url)
                bot.video_manager.save_data()
                await inter.followup.send(f"Saved `{short_url}` as `{name}` in `{colour}` database")
            else:
                await inter.followup.send("Error creating short URL.", ephemeral=True)

        else:
            await inter.followup.send("Invalid URL. Please provide a valid TikTok, Instagram, or Discord video URL.", ephemeral=True)

    @vid.autocomplete("colour")
    async def vid_autocomplete_colour(inter: ApplicationCommandInteraction, user_input: str):
        return await autocomp_colours(inter, user_input)