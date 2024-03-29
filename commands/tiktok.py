import os
import aiofiles
import disnake
import io
import re
import asyncio
from utils import download_media, fetch_tiktok_content, process_slideshow, resolve_short_url, extract_urls


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
            ),
            disnake.Option(
                "slideshow_length",
                "Length of each slide in the slideshow (in seconds). Default is 3 seconds.",
                type=disnake.OptionType.string,
                required=False
            )
        ] + [
            disnake.Option(
                f"url_{i}",
                f"TikTok URL #{i}.",
                type=disnake.OptionType.string,
                required=False
            ) for i in range(2, 11)
        ]
    )
    async def downloadtiktok(ctx, url1, caption=None, slideshow_length="3.0", **urls):
        try:
            slideshow_length = float(slideshow_length)
        except ValueError:
            await ctx.send("Invalid slideshow length. Please enter a valid number.", ephemeral=True)
            return

        if slideshow_length <= 0:
            await ctx.send("Slideshow length must be greater than zero.", ephemeral=True)
            return

        await ctx.send("Processing your request...", ephemeral=True)
        first_message = True

        extracted_urls = extract_urls(url1)
        if not extracted_urls:
            await ctx.send("No valid URL found in the first input.", ephemeral=True)
            return
        url1 = extracted_urls[0]

        urls = {'url1': url1, **urls}

        for url_key in sorted(urls.keys()):
            original_text = urls[url_key]
            if not original_text:
                continue

            extracted_urls = extract_urls(original_text)
            if not extracted_urls:
                await ctx.send(f"No valid URL found in {url_key}.", ephemeral=True)
                continue
            original_url = extracted_urls[0]

            resolved_url = await resolve_short_url(original_url, ctx.bot.http_session) if original_url.startswith("https://vm.tiktok.com/") else original_url
            tiktok_response = await fetch_tiktok_content(resolved_url, ctx.bot.http_session)

            if isinstance(tiktok_response, dict):
                if tiktok_response['type'] == 'video':
                    video_url = tiktok_response['video_url']
                    await send_video(ctx, video_url, caption, first_message)
                    first_message = False
                elif tiktok_response['type'] == 'slideshow':
                    slideshow_urls = tiktok_response['images']
                    audio_url = tiktok_response['music']
                    await send_slideshow(ctx, slideshow_urls, audio_url, slideshow_length, caption, first_message)
                    first_message = False
                else:
                    await ctx.send("Received unexpected response type.", ephemeral=True)
            else:
                await ctx.send("Failed to process the TikTok URL.", ephemeral=True)

    async def send_video(ctx, video_url, caption, first_message):
        video_data = await download_media(video_url, ctx.bot.http_session)
        if video_data:
            file_name = "TikTokVideo.mp4"
            if first_message:
                message_content = f"{ctx.author.mention}: {caption}" if caption else f"{ctx.author.mention} used /tiktok"
            else:
                message_content = None
            file = disnake.File(fp=video_data, filename=file_name)
            await ctx.channel.send(content=message_content, file=file)
        else:
            await ctx.send("Failed to download the video.", ephemeral=True)

    async def send_slideshow(ctx, slideshow_urls, audio_url, slideshow_length, caption, first_message):
        video_file, error_message = await process_slideshow(slideshow_urls, audio_url, ctx.bot.http_session, slideshow_length)
        if video_file:
            if first_message:
                message_content = f"{ctx.author.mention}: {caption}" if caption else f"{ctx.author.mention} used /tiktok"
            else:
                message_content = None
            async with aiofiles.open(video_file, 'rb') as f:
                file_content = await f.read()
            file = disnake.File(fp=io.BytesIO(file_content),
                                filename=os.path.basename(video_file))
            await ctx.channel.send(content=message_content, file=file)
            await asyncio.to_thread(os.remove, video_file)
        elif error_message:
            await ctx.send(error_message, ephemeral=True)
