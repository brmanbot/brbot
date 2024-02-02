import re
import aiosqlite
import disnake
import io
from datetime import datetime
from disnake import ApplicationCommandInteraction
import requests
from utils import bot, autocomp_colours, fetch_tiktok_content, shorten_url, has_role_check, insta_fetch_media
from database import add_video_to_database
from config import GUILD_IDS
from private_config import TIKTOK_ARCHIVE_CHANNEL, RAPID_API_KEY

async def fetch_content(session, url, content_type):
    if content_type == "tiktok":
        tiktok_response = await fetch_tiktok_content(url, session)
        if tiktok_response and isinstance(tiktok_response, dict):
            if tiktok_response['type'] == 'video':
                video_url = tiktok_response['video_url']
                tiktok_author_link = tiktok_response.get('author_link', None)
                tiktok_original_link = tiktok_response.get('original_link', None)
                tiktok_sound_link = tiktok_response.get('sound_link', None)
                return video_url, tiktok_author_link, tiktok_original_link, tiktok_sound_link
    elif content_type == "instagram":
        instagram_response = await insta_fetch_media(session, url)
        if instagram_response:
            return instagram_response['media_content'], None, instagram_response['original_link'], None
    elif content_type == "discord":
        return url, None, None, None

    return None, None, None, None

async def download_video(session, video_url):
    if not isinstance(video_url, str):
        print(f"Invalid video URL: {video_url}")
        return None

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
        if not await has_role_check(inter):
            await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        await inter.response.send_message("Processing your request...", ephemeral=True)
        date_added = datetime.now().strftime("%d/%m/%Y")
        added_by = f"{inter.user.name}#{inter.user.discriminator}"
        content_type = "tiktok" if "tiktok.com" in url else "instagram" if "instagram.com" in url else "discord" if url.startswith("https://cdn.discordapp.com/attachments/") or url.startswith("https://media.discordapp.net/attachments/") else None

        video_url, author_link, original_link, sound_link = await fetch_content(bot.http_session, url, content_type)
        tiktok_original_link = original_link if content_type == "tiktok" else None
        tiktok_sound_link = sound_link if content_type == "tiktok" else None  # Ensure tiktok_sound_link is defined

        if content_type == "instagram":
            original_link = normalize_instagram_url(original_link)
        insta_original_link = original_link if content_type == "instagram" else None

        conflict_details = await video_exists(name, None, url, tiktok_original_link, normalize_instagram_url(insta_original_link) if content_type == "instagram" else None)

        conflict_message = await create_conflict_message(conflict_details, bot.video_manager)
        if conflict_message:
            await inter.followup.send(f"Video(s) exist with same information:\n{conflict_message}", ephemeral=True)
            return

        short_url = await shorten_url(url) if content_type == "discord" else None
        if not short_url and content_type == "discord":
            await inter.followup.send("Error creating short URL.", ephemeral=True)
            return

        if content_type == "discord":
            await add_video_to_database(name, short_url, colour.lower(), url, added_by, None, tiktok_original_link, tiktok_sound_link, insta_original_link, date_added, bot.video_manager)
        elif video_url:
            video_data = await download_video(bot.http_session, video_url)
            if not video_data:
                await inter.followup.send("Failed to download video content.", ephemeral=True)
                return

            if upload_channel := bot.get_channel(int(TIKTOK_ARCHIVE_CHANNEL)):
                video_message = await upload_channel.send(file=disnake.File(fp=video_data, filename=f"{name}.mp4"))
                original_discord_url = video_message.attachments[0].url
                short_url = await shorten_url(original_discord_url)
                if not short_url:
                    await inter.followup.send("Error creating short URL.", ephemeral=True)
                    return

                await add_video_to_database(name, short_url, colour.lower(), original_discord_url, added_by, author_link, tiktok_original_link, tiktok_sound_link, insta_original_link, date_added, bot.video_manager)
            else:
                await inter.followup.send("Invalid upload channel ID.", ephemeral=True)
                return

        bot.video_manager.video_lists[colour.lower()].append(short_url)
        bot.video_manager.save_data()
        await inter.followup.send(f"Saved `{short_url}` as `{name}` in `{colour}` database.")

    def normalize_instagram_url(url):
        if "instagram.com" in url:
            url = url.rstrip('/')
            url = url.replace('/reel/', '/p/')
        return url

    @vid.autocomplete("colour")
    async def vid_autocomplete_colour(inter: ApplicationCommandInteraction, user_input: str):
        return await autocomp_colours(inter, user_input)