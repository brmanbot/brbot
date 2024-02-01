import asyncio
import datetime
import io
import json
import os
import re
import time
import aiofiles
import aiohttp
import aiosqlite
import pyshorteners
import disnake
from disnake.ext import commands
from disnake import ApplicationCommandInteraction
from disnake.ext.commands import InteractionBot
import requests
from PIL import Image, ImageOps
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, concatenate_audioclips
from moviepy.audio.fx.all import audio_loop
import numpy as np
import math
from concurrent.futures import ThreadPoolExecutor

from config import BOSSMANROLE_ID, ALLOWED_USER_ID, INTENTS, get_cooldown, update_cooldown
from database import fisher_yates_shuffle
from private_config import RAPID_API_KEY
from video_manager import VideoManager


print("Utils imported...")

class CustomBot(commands.InteractionBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cooldown = None
        self.update_cooldown()
        self.video_manager = None
        self.active_videos = {}
        self.http_session = aiohttp.ClientSession()

    @property
    def cooldown(self):
        self.update_cooldown()
        return self._cooldown

    def update_cooldown(self):
        self._cooldown = get_cooldown()

    async def close(self):
        await self.http_session.close()
        await super().close()

bot = CustomBot(intents=INTENTS)

async def setup_video_manager(bot):
    bot.video_manager = await VideoManager.create(bot)
    
setup_data = {"message_id": 0, "channel_id": 0, "target_channel_id": 0}


# Utility Functions
async def shorten_url(url: str) -> str:
    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(None, requests.get, 'https://da.gd/shorten?r=1&url={}'.format(url))
        response.raise_for_status()
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        print(f"Error shortening URL: {e}")
        return None
                                        

async def autocomp_colours(inter: ApplicationCommandInteraction, user_input: str):
    colours = ["Green", "Red", "Yellow"]
    suggestions = [colour for colour in colours if colour.startswith(user_input.lower())]
    return suggestions


async def autocomp_video_names(inter: ApplicationCommandInteraction, user_input: str):
    async with aiosqlite.connect("videos.db") as db:
        async with db.execute("SELECT name FROM videos WHERE name LIKE ? ORDER BY name ASC LIMIT 25", (f"%{user_input}%",)) as cursor:
            results = await cursor.fetchall()
            suggestions = [result[0] for result in results]
            return suggestions


async def has_role_check(ctx):
    if not ctx.author:
        return False
    user_roles = ctx.author.roles
    user_id = ctx.author.id
    is_bossman = disnake.utils.get(user_roles, id=BOSSMANROLE_ID) is not None
    is_allowed_user = user_id == ALLOWED_USER_ID
    return is_bossman or is_allowed_user


# Setup Data Management Functions
def load_setup_data(guild_id):
    guild_id = str(guild_id)
    if not os.path.exists("config_data.json"):
        return 0, 0, 0

    with open("config_data.json", "r") as f:
        data = json.load(f)

    if guild_id in data:
        return data[guild_id]["message_id"], data[guild_id]["channel_id"], data[guild_id]["target_channel_id"]
    else:
        return 0, 0, 0


def store_setup_data(guild_id, message_id, channel_id, target_channel_id):
    guild_id = str(guild_id)
    if not os.path.exists("config_data.json"):
        data = {}
    else:
        with open("config_data.json", "r") as f:
            data = json.load(f)

    data[guild_id] = {
        "message_id": message_id,
        "channel_id": channel_id,
        "target_channel_id": target_channel_id
    }

    with open("config_data.json", "w") as f:
        json.dump(data, f, indent=4)

    return None


# Role Timestamps Management Functions
def load_role_timestamps(guild_id):
    guild_id = str(guild_id)
    if os.path.exists("role_timestamps.json"):
        with open("role_timestamps.json", "r") as file:
            data = json.load(file)
        if guild_id in data:
            return data[guild_id]
    return {}


def store_role_timestamps(guild_id, user_id, removal_timestamp, role_id):
    guild_id = str(guild_id)
    user_id = str(user_id)
    role_id = str(role_id)
    with open("role_timestamps.json", "r") as file:
        data = json.load(file)
    if guild_id not in data:
        data[guild_id] = {}
    data[guild_id][user_id] = {"removal_timestamp": removal_timestamp, "role_id": role_id}
    with open("role_timestamps.json", "w") as file:
        json.dump(data, file)


def update_guild_role_timestamps(guild_id, role_timestamps):
    guild_id = str(guild_id)
    with open("role_timestamps.json", "r") as file:
        data = json.load(file)
    data[guild_id] = role_timestamps
    with open("role_timestamps.json", "w") as file:
        json.dump(data, file)


def load_all_role_timestamps():
    if os.path.exists("role_timestamps.json"):
        with open("role_timestamps.json", "r") as file:
            data = json.load(file)
        return data
    return {}


# Role Management Functions
async def schedule_role_removals(bot):
    role_removal_data = load_all_role_timestamps()
    for guild in bot.guilds:
        if str(guild.id) in role_removal_data:
            user_ids = list(role_removal_data[str(guild.id)].keys())
            for user_id in user_ids:
                user_data = role_removal_data[str(guild.id)][user_id]
                user_id = int(user_id)
                removal_timestamp = user_data['removal_timestamp']
                role_id = int(user_data['role_id'])
                removal_time = datetime.datetime.fromtimestamp(removal_timestamp)

                if removal_time <= datetime.datetime.now():
                    user = await guild.fetch_member(user_id)
                    role = guild.get_role(role_id)
                    if role in user.roles:
                        await user.remove_roles(role)

                    del role_removal_data[str(guild.id)][str(user_id)]
                    update_guild_role_timestamps(guild.id, role_removal_data[str(guild.id)])
                else:
                    async def remove_role_at_time():
                        await disnake.utils.sleep_until(removal_time)
                        user = await guild.fetch_member(user_id)
                        role = guild.get_role(role_id)
                        if role in user.roles:
                            await user.remove_roles(role)

                        del role_removal_data[str(guild.id)][str(user_id)]
                        update_guild_role_timestamps(guild.id, role_removal_data[str(guild.id)])

                    bot.loop.create_task(remove_role_at_time())


async def remove_role_after_duration(user, role_id, duration):
    await asyncio.sleep(duration)
    await remove_role(user, role_id)


async def remove_role(user, role_id):
    role = user.guild.get_role(role_id)
    if role in user.roles:
        await user.remove_roles(role)


async def remove_role_later(member, role_id, duration):
    removal_time = datetime.datetime.now() + datetime.timedelta(seconds=duration)
    store_role_timestamps(member.guild.id, member.id, removal_time.timestamp(), role_id)

    await disnake.utils.sleep_until(removal_time)
    role = member.guild.get_role(role_id)
    updated_member = await member.guild.fetch_member(member.id)
    if role in updated_member.roles:
        await updated_member.remove_roles(role)

    role_timestamps = load_role_timestamps(updated_member.guild.id)

    if str(updated_member.id) in role_timestamps:
        del role_timestamps[str(updated_member.id)]

    with open("role_timestamps.json", "w") as file:
        json.dump(role_timestamps, file)


# Instagram
re_instagram_post = re.compile(r'/p/([^/?]+)')
re_instagram_reel = re.compile(r'/reel/([^/?]+)')

async def insta_fetch_media(session, shortcode):
    url = "https://instagram230.p.rapidapi.com/post/details"
    querystring = {"shortcode": shortcode}
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "instagram230.p.rapidapi.com"
    }

    try:
        async with session.get(url, headers=headers, params=querystring) as response:
            if response.status == 200:
                data = await response.json()

                items = data.get('data', {}).get('xdt_api__v1__media__shortcode__web_info', {}).get('items', [])
                if items:
                    video_versions = items[0].get('video_versions', [])
                    if video_versions:
                        video_url = video_versions[0].get('url')
                        if video_url:
                            async with session.get(video_url) as video_response:
                                if video_response.status == 200:
                                    video_content = await video_response.read()
                                    file_extension = video_url.split('?')[0].split('.')[-1]
                                    return io.BytesIO(video_content), file_extension

                return None, None
            else:
                print(f"Failed to fetch media. Status code: {response.status}")
                return None, None
    except asyncio.TimeoutError:
        print("The request for downloading media timed out.")
        return None, None
    except Exception as e:
        print(f"Error occurred while fetching media: {e}")
        return None, None


async def insta_fetch_media_fallback(session, url, content_type, content_counter):
    rapidapi_url = "https://instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com/"
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com"
    }
    querystring = {"url": url}

    try:
        async with session.get(rapidapi_url, headers=headers, params=querystring) as response:
            if response.status == 200:
                response_data = await response.json()
                if response_data and isinstance(response_data, list) and "url" in response_data[0]:
                    media_url = response_data[0]["url"]
                    async with session.get(media_url) as media_response:
                        if media_response.status == 200:
                            media_content = await media_response.read()
                            file_extension = "mp4" if content_type.lower() == 'video' else "jpg"
                            filename = f"{content_type}_{content_counter}.{file_extension}"
                            return io.BytesIO(media_content), filename
                return None, None
            else:
                print(f"RapidAPI fallback failed: {response.status}")
                return None, None
    except asyncio.TimeoutError:
        print("The request for downloading media timed out.")
        return None, None
    except Exception as e:
        print(f"Error occurred while downloading media: {e}")
        return None, None


# TikTok    
async def resolve_short_url(url, http_session):
    async with http_session.head(url, allow_redirects=True) as response:
        return str(response.url)

async def fetch_tiktok_content_backup(url, http_session):
    tikwm_api_url = 'https://www.tikwm.com/api/'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json',
    }
    data = {'url': url}

    async with http_session.post(tikwm_api_url, headers=headers, data=data) as response:
        if response.status == 200:
            tikwm_response = await response.json()
            print("Backup Method Response:", tikwm_response)
            if tikwm_response['code'] == 0 and 'data' in tikwm_response:
                if 'images' in tikwm_response['data'] and 'music' in tikwm_response['data']:
                    images = tikwm_response['data']['images']
                    music_url = tikwm_response['data']['music']
                    return {'type': 'slideshow', 'images': images, 'music': music_url}
                elif 'play' in tikwm_response['data']:
                    video_url = tikwm_response['data'].get('play')
                    author_id = tikwm_response['data']['author']['id']
                    music_id = tikwm_response['data']['music_info']['id'] if 'music_info' in tikwm_response['data'] and 'id' in tikwm_response['data']['music_info'] else None
                    return {
                        'type': 'video',
                        'video_url': video_url,
                        'author_link': f"https://www.tiktok.com/@{author_id}",
                        'original_link': f"https://www.tiktok.com/@{author_id}/video/{tikwm_response['data']['id']}",
                        'sound_link': f"https://www.tiktok.com/music/original-sound-{music_id}" if music_id else None
                    }
            else:
                return {'error': "TikTok content could not be fetched or does not meet the expected format."}
        else:
            print("Backup Method Failed")
            return {'error': "Failed to fetch TikTok content."}

async def fetch_tiktok_content(url, http_session, timeout=0.2):
    if '/photo/' in url:
        url = url.replace('/photo/', '/video/')

    try:
        response = await asyncio.wait_for(
            http_session.post(
                "https://api.tik.fail/api/grab",
                headers={"User-Agent": "MyTikTokBot"},
                data={"url": url}
            ),
            timeout=timeout
        )

        if response.status == 200:
            data = await response.json()
            print("Normal Method Response:", data)
            if data.get("success"):
                return {
                    'type': 'video',
                    'video_url': data["data"]["download"]["video"].get("NoWM", {}).get("url"),
                    'author_link': data["data"]["metadata"]["AccountProfileURL"],
                    'original_link': data["data"]["metadata"]["VideoURL"],
                    'sound_link': data["data"]["metadata"]["AudioURL"]
                }
        else:
            print("Normal Method Failed, trying Backup Method")
            return await fetch_tiktok_content_backup(url, http_session)

    except asyncio.TimeoutError:
        print("Normal Method Timed Out, trying Backup Method")
        return await fetch_tiktok_content_backup(url, http_session)
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

async def download_media(url, http_session):
    async with http_session.get(url) as response:
        if response.status == 200:
            chunks = []
            async for chunk in response.content.iter_chunked(1024 * 1024):
                chunks.append(chunk)
            return io.BytesIO(b''.join(chunks))
        else:
            return None

async def create_audio_clip(audio_data):
    try:
        async with aiofiles.tempfile.NamedTemporaryFile(suffix='.mp3', mode='wb', delete=False) as tmp_audio:
            await tmp_audio.write(audio_data.getbuffer())
            tmp_audio_path = tmp_audio.name
        return AudioFileClip(tmp_audio_path), tmp_audio_path, None
    except Exception as e:
        return None, None, str(e)

def process_image(img, video_frame_size, slide_duration):
    try:
        aspect_ratio = img.width / img.height
        new_width = video_frame_size[0]
        new_height = int(new_width / aspect_ratio)

        img = img.resize((new_width, new_height), Image.LANCZOS)
        if new_height < video_frame_size[1]:
            padding_top = (video_frame_size[1] - new_height) // 2
            padding_bottom = video_frame_size[1] - new_height - padding_top
            img = ImageOps.expand(img, border=(0, padding_top, 0, padding_bottom), fill='black')

        img_clip = ImageClip(np.array(img)).set_duration(slide_duration)
        return img_clip
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

def create_image_clips(images_data, video_frame_size, slide_duration):
    clips = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_image, img_data, video_frame_size, slide_duration) 
                   for img_data in images_data if img_data is not None]
        for future in futures:
            clip = future.result()
            if clip:
                clips.append(clip)
    return clips

def calculate_optimal_video_size(images_data, max_width=1920, max_height=1080):
    average_aspect_ratio = sum((img.width / img.height for img in images_data if img is not None)) / len(images_data)

    if average_aspect_ratio > 1:
        width = max_width
        height = int(width / average_aspect_ratio)
    else:
        height = max_height
        width = int(height * average_aspect_ratio)

    if width > max_width:
        width = max_width
        height = int(width / average_aspect_ratio)
    if height > max_height:
        height = max_height
        width = int(height * average_aspect_ratio)

    return width, height

async def process_slideshow(image_urls, audio_url, http_session, slideshow_length=3):
    image_data_coroutines = [download_media(url, http_session) for url in image_urls]
    image_data_results = await asyncio.gather(*image_data_coroutines)
    images_data = [Image.open(io.BytesIO(result.getvalue())) if result else None for result in image_data_results]

    audio_data = await download_media(audio_url, http_session)
    if not audio_data:
        return None, "Failed to download audio."
    
    audio_clip, tmp_audio_path, error = await create_audio_clip(audio_data)
    if error:
        return None, error

    if not audio_clip:
        return None, "Audio clip creation failed."

    num_images = len([img for img in images_data if img is not None])

    if num_images == 1:
        slide_duration = audio_clip.duration
    else:
        slide_duration = slideshow_length
        
    slide_duration = slideshow_length
    max_duration_per_image = 6

    if not images_data or all(img is None for img in images_data):
        return None, "No images to process."

    video_frame_size = calculate_optimal_video_size(images_data)
    processed_clips = create_image_clips(images_data, video_frame_size, slide_duration)

    total_video_duration = len(processed_clips) * slide_duration
    total_loops = math.ceil(total_video_duration / (slide_duration * len(images_data)))

    final_clips = []
    for _ in range(total_loops):
        final_clips.extend(processed_clips)

    try:
        looped_audio_clip = audio_loop(audio_clip, duration=total_video_duration)

        async with aiofiles.tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_video:
            video_file_path = tmp_video.name
            video = concatenate_videoclips(final_clips, method="compose")
            final_video = video.set_audio(looped_audio_clip)
            final_video.write_videofile(video_file_path, codec="libx264", audio_codec="aac", fps=24)
            final_video.close()

    except Exception as e:
        return None, str(e)

    finally:
        if audio_clip:
            audio_clip.close()
        if tmp_audio_path and os.path.exists(tmp_audio_path):
            try:
                os.remove(tmp_audio_path)
            except Exception as e:
                print(f"Error removing temporary audio file: {e}")

    return video_file_path, None