import aiohttp
import disnake
import io
import re
from urllib.parse import quote, unquote

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


async def fetch_media_with_cobalt(session, url):
    encoded_url = quote(url, safe='')
    request_body = {
        "url": encoded_url,
        "vCodec": "h264",
        "vQuality": "1080p",
        "aFormat": "mp3",
        "filenamePattern": "classic",
        "isAudioOnly": False,
        "isNoTTWatermark": True,
        "isTTFullAudio": False,
        "isAudioMuted": False,
        "dubLang": False,
        "disableMetadata": False,
        "twitterGif": False,
    }
    headers = {**COMMON_HEADERS, "Accept": "application/json",
               "Content-Type": "application/json"}
    async with session.post("https://co.wuk.sh/api/json", json=request_body, headers=headers) as response:
        if response.status == 200:
            return await response.json()
        else:
            error_details = await response.text()
            print(
                f"Failed to fetch from Cobalt API: HTTP {response.status}, Details: {error_details}")
            return None


async def download_and_send_media(ctx, media_url, caption, session, first_media):
    try:
        async with session.head(media_url, headers=COMMON_HEADERS) as head_response:
            if head_response.status != 200 or int(head_response.headers.get('Content-Length', 0)) > (100 * 1024 * 1024):
                await ctx.send(f"Error processing\n{media_url}\nFile is too large (>100mb) or not accessible", ephemeral=True)
                return

        async with session.get(media_url, headers=COMMON_HEADERS) as media_response:
            if media_response.status == 200:
                content_disposition = media_response.headers.get(
                    'Content-Disposition', '')
                filename = unquote(re.findall(r'filename\*?=([^;]+)', content_disposition)[0].split(
                    "'")[-1]) if 'filename=' in content_disposition else media_url.split("/")[-1].split("?")[0]
                file = disnake.File(fp=io.BytesIO(await media_response.read()), filename=filename)

                message_content = f"{ctx.author.mention}: {caption}" if first_media and caption else f"{ctx.author.mention} used /fetch" if first_media else None
                await ctx.channel.send(content=message_content, file=file)

            else:
                await ctx.send(f"Failed to fetch media content for URL: {media_url}. HTTP {media_response.status}", ephemeral=True)
    except Exception as e:
        await ctx.send(f"Error processing {media_url}: {str(e)}", ephemeral=True)


async def process_urls(ctx, urls, caption, session, first_media):
    for url in urls:
        result = await fetch_media_with_cobalt(session, url)
        if result:
            status = result.get('status')
            if status in ['picker', 'success', 'stream', 'redirect']:
                media_items = result.get(
                    'picker', []) if status == 'picker' else [result]
                for item in media_items:
                    media_url = item.get('url')
                    if media_url:
                        await download_and_send_media(ctx, media_url, caption if first_media else None, session, first_media)
                        first_media = False  # Update after the first media has been processed
            else:
                await ctx.send(f"Failed to process URL: {url}.", ephemeral=True)
        else:
            await ctx.send(f"Failed to fetch media for URL: {url}.", ephemeral=True)
    return first_media


def setup(bot):
    @bot.slash_command(
        name="fetch",
        description="Fetch media from various sources.",
        options=[
            disnake.Option(name="url", description="Enter the media URL.",
                           type=disnake.OptionType.string, required=True),
            disnake.Option(name="caption", description="Optional caption for the media.",
                           type=disnake.OptionType.string, required=False)
        ] + [
            disnake.Option(name=f"url_{i}", description=f"Additional media URL #{i}.", type=disnake.OptionType.string, required=False) for i in range(2, 11)
        ]
    )
    async def fetch_media(ctx, url, caption=None, **urls):
        await ctx.send("Processing your request...", ephemeral=True)
        all_urls = [url] + [value for key, value in urls.items() if value]

        async with aiohttp.ClientSession() as session:
            first_media = True
            for media_url in all_urls:
                first_media = await process_urls(ctx, [media_url], caption, session, first_media)
