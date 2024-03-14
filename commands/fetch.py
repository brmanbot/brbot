import aiohttp
import disnake
import io
import re
from urllib.parse import quote, unquote

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


async def fetch_media_with_cobalt(session, url, quality="1080p", audio_only=False):
    encoded_url = quote(url, safe='')
    request_body = {
        "url": encoded_url,
        "vCodec": "h264",
        "vQuality": quality.lower(),
        "aFormat": "mp3",
        "filenamePattern": "classic",
        "isAudioOnly": audio_only,
        "isNoTTWatermark": True,
        "isTTFullAudio": False,
        "isAudioMuted": False,
        "dubLang": False,
        "disableMetadata": False,
        "twitterGif": True,
    }
    headers = {**COMMON_HEADERS, "Accept": "application/json",
               "Content-Type": "application/json"}

    # # Print the request URL and body for debugging
    # print(f"Request URL: https://co.wuk.sh/api/json")
    # print(f"Request Body: {request_body}")

    async with session.post("https://co.wuk.sh/api/json", json=request_body, headers=headers) as response:
        response_text = await response.text()  # Capture the response text
        if response.status == 200:
            # # Print the API response for debugging
            # print(f"API Response: {response_text}")
            return await response.json()
        else:
            error_details = response_text  # Use the captured text
            print(
                f"Failed to fetch from Cobalt API: HTTP {response.status}, Details: {error_details}")
            return None


async def download_and_send_media(ctx, media_url, caption, session, first_media):
    try:
        async with session.head(media_url, headers=COMMON_HEADERS) as head_response:
            content_length = head_response.headers.get('Content-Length', 0)
            if head_response.status != 200 or int(content_length) > (100 * 1024 * 1024):
                error_message = f"Error: {media_url} is too large (>100MB) or not accessible."
                if len(error_message) > 2000:
                    error_message = error_message[:1997] + "..."
                await ctx.send(error_message, ephemeral=True)
                return

        async with session.get(media_url, headers=COMMON_HEADERS) as media_response:
            if media_response.status == 200:
                content_disposition = media_response.headers.get(
                    'Content-Disposition', '')
                filename_regex = r'filename\*?=([^;]+)'
                filename_list = re.findall(filename_regex, content_disposition)
                filename = (unquote(filename_list[0].split(
                    "'")[-1]) if filename_list else media_url.split("/")[-1].split("?")[0])

                file = disnake.File(fp=io.BytesIO(await media_response.read()), filename=filename)

                if first_media and caption:
                    message_content = f"{ctx.author.mention}: {caption}"
                elif first_media:
                    message_content = f"{ctx.author.mention} used /fetch"
                else:
                    message_content = None

                if message_content and len(message_content) > 2000:
                    message_content = message_content[:1997] + "..."
                await ctx.channel.send(content=message_content, file=file)
            else:
                await ctx.send(f"Failed to fetch media content for URL: {media_url}. HTTP {media_response.status}", ephemeral=True)
    except Exception as e:
        error_message = f"Error processing {media_url}: {str(e)}"
        if len(error_message) > 2000:
            error_message = error_message[:1997] + "..."
        await ctx.send(error_message, ephemeral=True)


async def process_urls(ctx, urls, caption, session, first_media, quality="1080p", audio_only=False):
    for url in urls:
        result = await fetch_media_with_cobalt(session, url, quality, audio_only)
        if result:
            status = result.get('status')
            if status in ['picker', 'success', 'stream', 'redirect']:
                media_items = result.get(
                    'picker', []) if status == 'picker' else [result]
                for item in media_items:
                    media_url = item.get('url')
                    if media_url:
                        await download_and_send_media(ctx, media_url, caption if first_media else None, session, first_media)
                        first_media = False
            else:
                await ctx.send(f"Failed to process URL: {url}.", ephemeral=True)
        else:
            await ctx.send(f"Failed to fetch media for URL: {url}."+"\nCheck API status: https://status.cobalt.tools/", ephemeral=True)
    return first_media


def setup(bot):
    @bot.slash_command(
        name="fetch",
        description="Fetch media from various sources.",
        options=[
            disnake.Option(name="url", description="Enter the media URL.",
                           type=disnake.OptionType.string, required=True),
            disnake.Option(name="quality", description="Select the video quality.", type=disnake.OptionType.string, required=False, choices=[
                disnake.OptionChoice(name="1080p", value="1080p"),
                disnake.OptionChoice(name="720p", value="720p"),
                disnake.OptionChoice(name="480p", value="480p"),
                disnake.OptionChoice(name="360p", value="360p"),
            ]),
            disnake.Option(name="audio_only", description="Fetch audio only.",
                           type=disnake.OptionType.boolean, required=False),
            disnake.Option(name="caption", description="Optional caption for the media.",
                           type=disnake.OptionType.string, required=False)
        ] + [
            disnake.Option(name=f"url_{i}", description=f"Additional media URL #{i}.", type=disnake.OptionType.string, required=False) for i in range(2, 11)
        ]
    )
    async def fetch_media(ctx, url, quality="1080p", audio_only=False, caption=None, **urls):
        await ctx.send("Processing your request...", ephemeral=True)
        all_urls = [url] + [value for key, value in urls.items() if value]

        async with aiohttp.ClientSession() as session:
            first_media = True
            first_media = await process_urls(ctx, all_urls, caption, session, first_media, quality, audio_only)
