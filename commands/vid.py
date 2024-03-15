import io
from datetime import datetime
import re

import aiosqlite
import disnake
import requests
from disnake import ApplicationCommandInteraction, OptionChoice

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


def normalize_discord_url(url: str) -> str:
    parsed_url = urlparse(url)
    if 'cdn.discordapp.com' in parsed_url.netloc or 'media.discordapp.net' in parsed_url.netloc:
        netloc = 'cdn.discordapp.com' if 'media.discordapp.net' in parsed_url.netloc else parsed_url.netloc
        normalized_url = f"{parsed_url.scheme}://{netloc}{parsed_url.path}"
        return normalized_url
    return None


def normalize_hashtags(hashtags: list[str]) -> str:
    if not isinstance(hashtags, list):
        hashtags = [hashtags]

    normalized_hashtags_list = [
        tag.strip('#').lower() for tag in hashtags if tag]
    normalized_hashtags = ','.join(sorted(set(normalized_hashtags_list)))

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
                name=f"hashtag_1",
                description=f"Hashtag 1.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_2",
                description=f"Hashtag 2.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_3",
                description=f"Hashtag 3.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_4",
                description=f"Hashtag 4.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_5",
                description=f"Hashtag 5.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_6",
                description=f"Hashtag 6.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_7",
                description=f"Hashtag 7.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_8",
                description=f"Hashtag 8.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_9",
                description=f"Hashtag 9.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_10",
                description=f"Hashtag 10.",
                type=disnake.OptionType.string,
                required=False,
            )
        ]
    )
    async def vid(inter: ApplicationCommandInteraction, colour: str, name: str, url: str, **kwargs):
        if not await has_role_check(inter):
            await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        hashtags = [kwargs[f"hashtag_{i}"]
                    for i in range(1, 11) if f"hashtag_{i}" in kwargs]
        normalized_hashtags = normalize_hashtags(','.join(hashtags))

        await inter.response.send_message("Processing your request...", ephemeral=True)

        extracted_urls = extract_urls(url)
        if not extracted_urls:
            await inter.followup.send("No valid URL found in the provided text.", ephemeral=True)
            return

        content_type = "tiktok" if "tiktok.com" in extracted_urls[
            0] else "instagram" if "instagram.com" in extracted_urls[0] else "discord"

        if content_type == "discord":
            normalized_url = normalize_discord_url(extracted_urls[0])
            if normalized_url is None:
                await inter.followup.send("The provided URL is invalid. Please use a valid Discord attachment URL.", ephemeral=True)
                return
        else:
            normalized_url = extracted_urls[0]

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
            await inter.followup.send(f"Conflict detected:\n{conflict_message}", ephemeral=True)
            return

        final_url_for_storage = None

        if content_type in ["tiktok", "instagram"]:
            video_data = await download_video(bot.http_session, video_url)
            if not video_data:
                await inter.followup.send("Failed to download video content.", ephemeral=True)
                return

            if upload_channel := bot.get_channel(int(TIKTOK_ARCHIVE_CHANNEL)):
                video_message = await upload_channel.send(file=disnake.File(fp=video_data, filename=f"{name}.mp4"))
                discord_video_url = video_message.attachments[0].url
                normalized_discord_url = normalize_discord_url(
                    discord_video_url)
                final_url_for_storage = await shorten_url(normalized_discord_url)
            else:
                await inter.followup.send("Invalid upload channel ID.", ephemeral=True)
                return
        elif content_type == "discord":
            normalized_discord_url = normalize_discord_url(extracted_urls[0])
            if normalized_discord_url is None:
                await inter.followup.send("The provided URL is invalid. Please use a valid Discord attachment URL.", ephemeral=True)
                return
            final_url_for_storage = await shorten_url(normalized_discord_url)

        if not final_url_for_storage:
            await inter.followup.send("Failed to process the video URL.", ephemeral=True)
            return

        await bot.video_manager.add_video_to_database(
            name=name,
            url=final_url_for_storage,
            color=colour.lower(),
            original_url=normalized_discord_url,
            added_by=added_by,
            tiktok_author_link=author_link if content_type == "tiktok" else None,
            tiktok_original_link=tiktok_original_link,
            tiktok_sound_link=sound_link if content_type == "tiktok" else None,
            insta_original_link=insta_original_link,
            date_added=date_added,
            hashtags=normalized_hashtags
        )

        await bot.video_manager.add_video_to_cache(
            name=name,
            url=final_url_for_storage,
            color=colour.lower(),
            original_url=normalized_discord_url,
            added_by=added_by,
            tiktok_author_link=author_link if content_type == "tiktok" else None,
            tiktok_original_link=tiktok_original_link,
            tiktok_sound_link=sound_link if content_type == "tiktok" else None,
            insta_original_link=insta_original_link,
            date_added=date_added,
            hashtags=normalized_hashtags,
            is_hall_of_fame=0
        )

        bot.video_manager.save_data()
        if normalized_hashtags:
            hashtags_message = f"with hashtags: `{normalized_hashtags}`"
        else:
            hashtags_message = "with no hashtags"

        await inter.followup.send(f"Saved `{name}` in the `{colour}` database {hashtags_message}.", ephemeral=True)

    @vid.autocomplete("colour")
    async def vid_autocomplete_colour(inter: ApplicationCommandInteraction, user_input: str):
        return await autocomp_colours(inter, user_input)

    async def autocomplete_hashtag(inter: ApplicationCommandInteraction, user_input: str):
        all_hashtags = await fetch_all_hashtags()
        filtered_hashtags = [
            ht for ht in all_hashtags if user_input.lower() in ht.lower()]
        return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]

    hashtag_option_names = [f"hashtag_{i}" for i in range(1, 11)]
    for option_name in hashtag_option_names:
        vid.autocomplete(option_name)(autocomplete_hashtag)
