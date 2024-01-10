import asyncio
import disnake
import re
import io
from private_config import RAPID_API_KEY

async def fetch_media(session, url, content_type, content_counter, ctx):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                media_content = await response.read()
                file_extension = "mp4" if content_type == 'video' else "jpg"
                filename = f"{content_type}_{content_counter}.{file_extension}"
                return io.BytesIO(media_content), filename
            else:
                await ctx.send(
                    f"Failed to download media from {url}. Response code: {response.status}",
                    ephemeral=True
                )
                return None, None
    except Exception as e:
        await ctx.send(
            f"Error occurred while downloading media: {e}",
            ephemeral=True
        )
        return None, None

async def process_urls(ctx, urls, caption, session):
    tasks = []
    content_counter = 1

    for url in urls:
        if not url or not re.match(r'https?://www\.instagram\.com/([a-zA-Z0-9_.]+/)?(p|reel)/[a-zA-Z0-9-_]+', url):
            await ctx.send(f"Invalid Instagram URL: {url}", ephemeral=True)
            continue

        api_url = "https://instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com/"
        querystring = {"url": url}
        headers = {
            "X-RapidAPI-Key": RAPID_API_KEY,
            "X-RapidAPI-Host": "instagram-downloader-download-instagram-videos-stories1.p.rapidapi.com"
        }

        try:
            async with session.get(api_url, headers=headers, params=querystring) as response:
                if response.status == 200:
                    data = await response.json()

                    if isinstance(data, list):
                        for content in data:
                            if "url" in content:
                                task = fetch_media(session, content["url"], content.get("type", "video"), content_counter, ctx)
                                tasks.append(task)
                                content_counter += 1
                    else:
                        await ctx.send(f"API response error for URL {url}: {data}", ephemeral=True)
                else:
                    await ctx.send(
                        f"Failed to communicate with the API for URL {url}. Status code: {response.status}",
                        ephemeral=True
                    )
        except Exception as e:
            await ctx.send(
                f"Error occurred while communicating with the API: {e}",
                ephemeral=True
            )

    results = await asyncio.gather(*[task for task in tasks if task is not None])
    first_message = True
    for media_buffer, filename in results:
        if media_buffer and filename:
            if first_message:
                message_content = f"{ctx.author.mention}: {caption}" if caption else f"{ctx.author.mention} used /insta"
                first_message = False
            else:
                message_content = None

            file = disnake.File(fp=media_buffer, filename=filename)
            await ctx.channel.send(content=message_content, file=file)
            media_buffer.close()

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