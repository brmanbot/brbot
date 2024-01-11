import os
import disnake
from disnake.ext import commands
import aiohttp
import io
import re
import asyncio
from utils import bot
from PIL import Image
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip
import tempfile
import numpy as np
import math

async def resolve_short_url(url, http_session):
    async with http_session.head(url, allow_redirects=True) as response:
        return str(response.url)

async def fetch_tiktok_content(url, http_session):
    if '/photo/' in url:
        url = url.replace('/photo/', '/video/')

    async with http_session.post(
        "https://api.tik.fail/api/grab",
        headers={"User-Agent": "MyTikTokBot"},
        data={"url": url}
    ) as response:
        if response.status == 200:
            return await response.json()
        else:
            return None

async def download_media(url, http_session):
    async with http_session.get(url) as response:
        if response.status == 200:
            return io.BytesIO(await response.read())
        else:
            return None

async def create_audio_clip(audio_data):
    try:
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_audio:
            tmp_audio.write(audio_data.getbuffer())
            tmp_audio.flush()
            audio_clip = AudioFileClip(tmp_audio.name)
            return audio_clip, None
    except Exception as e:
        return None, str(e)

def create_image_clips(images_data, video_frame_size, slide_duration):
    clips = []
    for image_data in images_data:
        with Image.open(image_data) as img:
            img = img.convert('RGB')
            img.thumbnail(video_frame_size, Image.LANCZOS)
            if img.size != video_frame_size:
                new_img = Image.new('RGB', video_frame_size)
                new_img.paste(img, ((video_frame_size[0] - img.width) // 2, (video_frame_size[1] - img.height) // 2))
                img = new_img

            img_clip = ImageClip(np.array(img)).set_duration(slide_duration)
            clips.append(img_clip)
    return clips

def generate_video(clips, audio_clip, total_video_duration):
    try:
        video = concatenate_videoclips(clips, method="compose")
        final_video = video.set_audio(audio_clip.subclip(0, total_video_duration))
        final_video.write_videofile("slideshow_video.mp4", codec="libx264", fps=24)
        return "slideshow_video.mp4", None
    except Exception as e:
        return None, str(e)

async def process_slideshow(image_urls, audio_url, http_session):
    images_data = await asyncio.gather(*[download_media(url, http_session) for url in image_urls])
    audio_data = await download_media(audio_url, http_session)

    if not audio_data:
        return None, "Failed to download audio."

    audio_clip, error = await create_audio_clip(audio_data)
    if error:
        return None, error

    if not audio_clip:
        return None, "Audio clip creation failed."

    slide_duration = 3
    max_duration_per_image = 6

    if not images_data:
        return None, "No images to process."

    with Image.open(images_data[0]) as first_image:
        video_frame_size = first_image.size

    total_video_duration = min(len(images_data) * max_duration_per_image, audio_clip.duration)
    total_loops = math.ceil(total_video_duration / (slide_duration * len(images_data)))

    clips = []
    for _ in range(total_loops):
        new_clips = create_image_clips(images_data, video_frame_size, slide_duration)
        clips.extend(new_clips)

    return generate_video(clips, audio_clip, total_video_duration)

def setup(bot):
    @bot.slash_command(
        name="tiktok",
        description="Process TikTok videos for easy viewing.",
        options=[
            disnake.Option(
                "url1",
                "First TikTok URL.",
                type=disnake.OptionType.string,
                required=True
            ),
            disnake.Option(
                "caption",
                "Replace the `@user used /tiktok` message with your own.",
                type=disnake.OptionType.string,
                required=False
            )
        ] + [
            disnake.Option(
                f"url{i}",
                f"TikTok URL #{i}.",
                type=disnake.OptionType.string,
                required=False
            ) for i in range(2, 11)
        ]
    )
    async def downloadtiktok(ctx, url1, caption=None, **urls):
        await ctx.send("Processing your request...", ephemeral=True)
        first_message = True

        urls = {'url1': url1, **urls}

        for url_key in sorted(urls.keys()):
            original_url = urls[url_key]
            if not original_url:
                continue

            resolved_url = await resolve_short_url(original_url, bot.http_session) if original_url.startswith("https://vm.tiktok.com/") else original_url
            tiktok_response = await fetch_tiktok_content(resolved_url, bot.http_session)

            if tiktok_response and tiktok_response.get("success"):
                author_id = tiktok_response["data"]["metadata"]["AccountUserName"]
                timestamp = tiktok_response["data"]["metadata"]["timestamp"]

                if 'resource' in tiktok_response['data'] and tiktok_response['data']['resource'] == 'slideshow':
                    video_id = re.findall(r'video/(\d+)', tiktok_response["data"]["metadata"]["VideoURL"])[0]
                    audio_url = f"https://www.tikwm.com/video/media/play/{video_id}.mp4"

                    slideshow_urls = tiktok_response['data']['download']
                    video_file, error_message = await process_slideshow(slideshow_urls, audio_url, bot.http_session)
                    
                    if video_file:
                        try:
                            if first_message:
                                message_content = f"{ctx.author.mention}: {caption}" if caption else f"{ctx.author.mention} used /tiktok"
                                first_message = False
                            else:
                                message_content = None

                            file = disnake.File(video_file)
                            await ctx.channel.send(content=message_content, file=file)
                            os.remove(video_file)
                        except disnake.HTTPException as e:
                            await ctx.send(f"An error occurred while uploading the video: {e}", ephemeral=True)
                    else:
                        await ctx.send(error_message, ephemeral=True)
                else:
                    video_url = tiktok_response["data"]["download"]["video"].get("NoWM", {}).get("url")
                    video_data = await download_media(video_url, bot.http_session)

                    if video_data:
                        try:
                            file_name = f"{author_id}_{timestamp}.mp4"
                            if first_message:
                                message_content = f"{ctx.author.mention}: {caption}" if caption else f"{ctx.author.mention} used /tiktok"
                                first_message = False
                            else:
                                message_content = None
                            file = disnake.File(fp=video_data, filename=file_name)
                            await ctx.channel.send(content=message_content, file=file)
                            video_data.close()
                        except disnake.HTTPException as e:
                            if e.status == 413:
                                await ctx.send("The video file is too large to upload.", ephemeral=True)
                            else:
                                await ctx.send(f"An error occurred while uploading the video: {e}", ephemeral=True)
                        except Exception as e:
                            await ctx.send(f"An unexpected error occurred: {e}", ephemeral=True)
                    else:
                        await ctx.channel.send(f"Failed to download the video. Original link: {original_url}", ephemeral=True)
            else:
                await ctx.followup.send(f"Failed to fetch TikTok content. Here's the original link: {original_url}", ephemeral=True)