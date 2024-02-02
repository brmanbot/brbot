import asyncio
import disnake
import re
import io
from private_config import RAPID_API_KEY

import aiohttp
import asyncio
import io
import re
import json
from private_config import RAPID_API_KEY
from utils import insta_fetch_media, insta_fetch_media_fallback

re_instagram_post = re.compile(r'/p/([^/?]+)')
re_instagram_reel = re.compile(r'/reel/([^/?]+)')


async def process_urls(ctx, urls, caption, session):
    primary_tasks = []
    fallback_tasks = []
    content_counter = 1

    for url in urls:
        match = re_instagram_post.search(url) or re_instagram_reel.search(url)
        if match:
            shortcode = match.group(1)
            primary_tasks.append(asyncio.create_task(insta_fetch_media(session, url)))
        else:
            await ctx.send(f"Invalid Instagram URL: {url}", ephemeral=True)
            continue

    primary_results = await asyncio.gather(*primary_tasks, return_exceptions=True)

    for url, result in zip(urls, primary_results):
        if isinstance(result, Exception) or result is None or result.get('media_content') is None:
            fallback_tasks.append(asyncio.create_task(insta_fetch_media_fallback(session, url, "video", content_counter)))
            content_counter += 1

    fallback_results = await asyncio.gather(*fallback_tasks, return_exceptions=True) if fallback_tasks else []

    combined_results = []
    fallback_index = 0
    for result in primary_results:
        if isinstance(result, Exception) or result is None or result.get('media_content') is None:
            combined_results.append(fallback_results[fallback_index])
            fallback_index += 1
        else:
            combined_results.append(result)

    first_message = True
    for result in combined_results:
        if result and result.get('media_content'):
            media_url = result['media_content']
            async with session.get(media_url) as media_response:
                if media_response.status == 200:
                    media_content = await media_response.read()
                    file_extension = result.get('file_extension', 'mp4')
                    filename = f"media_{content_counter}.{file_extension}"

                    if first_message:
                        message_content = f"{ctx.author.mention}: {caption}" if caption else f"{ctx.author.mention} used /insta"
                        first_message = False
                    else:
                        message_content = None

                    file = disnake.File(fp=io.BytesIO(media_content), filename=filename)
                    await ctx.channel.send(content=message_content, file=file)
                    content_counter += 1
        else:
            print(f"Failed to process URL: {result.get('original_link', 'Unknown URL')}")

def setup(bot):
    @bot.slash_command(
        name="insta",
        description="Process Instagram Reels and Posts for easy viewing.",
        options=[
            disnake.Option(
                "url1",
                "First Instagram URL.",
                type=disnake.OptionType.string,
                required=True
            ),
            disnake.Option(
                "caption",
                "Replace the `@user used /insta` message with your own.",
                type=disnake.OptionType.string,
                required=False
            )
        ] + [
            disnake.Option(
                f"url{i}",
                f"Instagram URL #{i}.",
                type=disnake.OptionType.string,
                required=False
            ) for i in range(2, 11)
        ]
    )
    async def downloadreel(ctx, **inputs):
        await ctx.send("Processing your request...", ephemeral=True)
        urls = [inputs.get(f"url{i}") for i in range(1, 11)]
        caption = inputs.get("caption")
        urls = [url for url in urls if url is not None]

        await process_urls(ctx, urls, caption, bot.http_session)