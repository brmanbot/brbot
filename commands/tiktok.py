import os
import aiofiles
import disnake
from disnake.ext import commands
import aiohttp
import io
import re
import asyncio
from utils import bot
from PIL import Image, ImageOps
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, concatenate_audioclips
from moviepy.audio.fx.all import audio_loop
import numpy as np
import math
from concurrent.futures import ThreadPoolExecutor

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

async def process_slideshow(image_urls, audio_url, http_session):
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

    slide_duration = 3
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
            if original_url.startswith("https://vm.tiktok.com/"):
                resolved_url = await resolve_short_url(original_url, bot.http_session)
            else:
                resolved_url = original_url

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

                            async with aiofiles.open(video_file, 'rb') as f:
                                file_content = await f.read()
                            file = disnake.File(fp=io.BytesIO(file_content), filename=os.path.basename(video_file))
                            await ctx.channel.send(content=message_content, file=file)
                            await asyncio.to_thread(os.remove, video_file)
                        except disnake.HTTPException as e:
                            await ctx.send(f"An error occurred while uploading the video: {e}", ephemeral=True)
                        except Exception as e:
                            await ctx.send(f"An unexpected error occurred: {e}", ephemeral=True)
                    elif error_message:
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
                video_id_match = re.search(r'/video/(\d+)', resolved_url)
                if video_id_match:
                    video_id = video_id_match.group(1)
                    backup_url = f"https://www.tikwm.com/video/media/play/{video_id}.mp4"
                    print(f"Attempting backup method for video ID {video_id} with URL: {backup_url}")  # Debug print

                    video_data = await download_media(backup_url, bot.http_session)

                    if video_data:
                        try:
                            file_name = f"{video_id}.mp4"
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
                        print(f"Failed to download the video using the backup method. URL: {backup_url}")  # Debug print
                else:
                    print(f"No valid video ID found in URL: {resolved_url}")  # Debug print
                    await ctx.channel.send(f"Failed to fetch TikTok content and could not find a valid video ID in the URL. Here's the original link: {original_url}", ephemeral=True)