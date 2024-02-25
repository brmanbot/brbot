import io
from datetime import datetime
import re

import aiosqlite
import disnake
import requests
from disnake import ApplicationCommandInteraction

from config import GUILD_IDS
from private_config import TIKTOK_ARCHIVE_CHANNEL
from urllib.parse import urlparse
from utils import (
    bot, autocomp_colours, fetch_all_hashtags, fetch_tiktok_content, shorten_url,
    has_role_check, insta_fetch_media, extract_urls
)


async def fetch_content(session, url, content_type):
    if content_type == "tiktok":
        tiktok_response = await fetch_tiktok_content(url, session)
        if tiktok_response and isinstance(tiktok_response, dict):
            if tiktok_response['type'] == 'video':
                video_url = tiktok_response['video_url']
                tiktok_author_link = tiktok_response.get('author_link', None)
                tiktok_original_link = tiktok_response.get(
                    'original_link', None)
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


async def video_exists(name, original_discord_url, tiktok_original_link, insta_original_link, db_path="videos.db"):
    query = """
    SELECT name, original_url, tiktok_original_link, insta_original_link 
    FROM videos 
    WHERE name = ? OR original_url = ? OR tiktok_original_link = ? OR insta_original_link = ?
    """
    params = (name, original_discord_url,
              tiktok_original_link, insta_original_link)
    conflict_details = []
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                video_name, original_url, tiktok_link, insta_link = row
                if video_name == name:
                    conflict_details.append(("Name", original_url))
                if original_discord_url and original_url == original_discord_url:
                    conflict_details.append(("Discord URL", original_url))
                if tiktok_original_link and tiktok_link == tiktok_original_link:
                    conflict_details.append(("TikTok URL", original_url))
                if insta_original_link and insta_link == insta_original_link:
                    conflict_details.append(("Instagram URL", original_url))
    return conflict_details


async def create_conflict_message(conflict_details, video_manager):
    conflict_messages = []
    for conflict_type, url in conflict_details:
        video_info = await video_manager.fetch_video_info(url)
        if video_info:
            video_name = video_info['name']
            conflict_messages.append(f"{conflict_type}: [{video_name}]({url})")
    return "\n".join(conflict_messages)


def normalize_discord_url(url):
    parsed_url = urlparse(url)
    if 'cdn.discordapp.com' in parsed_url.netloc or 'media.discordapp.net' in parsed_url.netloc:
        normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        return normalized_url
    return url


def normalize_hashtags(hashtags: str) -> str:
    hashtag_list = [tag.strip('#').lower()
                    for tag in re.split('[, ]+', hashtags.strip())]
    unique_hashtags = sorted(set(hashtag_list))
    normalized_hashtags = ','.join(unique_hashtags)

    return normalized_hashtags


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
            ),
            disnake.Option(
                "hashtags",
                "Enter hashtags related to the video, separated by commas, to improve searchability.",
                type=disnake.OptionType.string,
                required=False
            )
        ]
    )
    async def vid(inter: ApplicationCommandInteraction, colour: str, name: str, url: str, hashtags: str = ""):
        if not await has_role_check(inter):
            await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        await inter.response.send_message("Processing your request...", ephemeral=True)

        extracted_urls = extract_urls(url)
        if not extracted_urls:
            await inter.followup.send("No valid URL found in the provided text.", ephemeral=True)
            return
        normalized_url = normalize_discord_url(extracted_urls[0])

        content_type = "tiktok" if "tiktok.com" in normalized_url else "instagram" if "instagram.com" in normalized_url else "discord"
        date_added = datetime.now().strftime("%d/%m/%Y")
        added_by = f"{inter.user.name}#{inter.user.discriminator}"

        video_url, author_link, original_link, sound_link = await fetch_content(bot.http_session, normalized_url, content_type)
        original_discord_url = normalized_url if content_type == "discord" else None
        tiktok_original_link = original_link if content_type == "tiktok" else None
        insta_original_link = original_link if content_type == "instagram" else None

        normalized_hashtags = normalize_hashtags(
            hashtags)

        conflict_details = await bot.video_manager.video_exists(
            name, original_discord_url, tiktok_original_link, insta_original_link)

        if conflict_details:
            conflict_message = await create_conflict_message(conflict_details, bot.video_manager)
            await inter.followup.send(f"Video(s) exist with the same information:\n{conflict_message}", ephemeral=True)
            return

        if content_type in ["tiktok", "instagram"]:
            video_data = await download_video(bot.http_session, video_url)
            if not video_data:
                await inter.followup.send("Failed to download video content.", ephemeral=True)
                return

            if upload_channel := bot.get_channel(int(TIKTOK_ARCHIVE_CHANNEL)):
                video_message = await upload_channel.send(file=disnake.File(fp=video_data, filename=f"{name}.mp4"))
                original_discord_url = video_message.attachments[0].url
                short_url = await shorten_url(original_discord_url)
            else:
                await inter.followup.send("Invalid upload channel ID.", ephemeral=True)
                return
        elif content_type == "discord":
            short_url = await shorten_url(url)

        await bot.video_manager.add_video_to_database(
            name=name,
            url=short_url,
            color=colour.lower(),
            original_url=original_discord_url,
            added_by=added_by,
            tiktok_author_link=author_link if content_type == "tiktok" else None,
            tiktok_original_link=tiktok_original_link,
            tiktok_sound_link=sound_link if content_type == "tiktok" else None,
            insta_original_link=insta_original_link,
            date_added=date_added,
            hashtags=normalized_hashtags
        )

        bot.video_manager.save_data()
        await inter.followup.send(f"Saved `{name}` in the `{colour}` database with hashtags: `{normalized_hashtags}`.", ephemeral=True)

    @vid.autocomplete("hashtags")
    async def hashtags_autocomplete(inter: ApplicationCommandInteraction, user_input: str):
        all_hashtags = await fetch_all_hashtags()
        filtered_hashtags = [
            hashtag for hashtag in all_hashtags if hashtag.startswith(user_input.lower())]
        unique_filtered_hashtags = list(set(filtered_hashtags))[:25]
        return [disnake.OptionChoice(name=hashtag, value=hashtag) for hashtag in unique_filtered_hashtags]

    @vid.autocomplete("colour")
    async def vid_autocomplete_colour(inter: ApplicationCommandInteraction, user_input: str):
        return await autocomp_colours(inter, user_input)
