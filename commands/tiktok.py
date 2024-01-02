import disnake
from disnake.ext import commands
import aiohttp
import io
import re
import asyncio
from utils import bot

async def resolve_short_url(url, http_session):
    async with http_session.head(url, allow_redirects=True) as response:
        return str(response.url)

async def fetch_tiktok_content(url, http_session):
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

async def process_slideshow(urls, http_session):
    tasks = [download_media(url, http_session) for url in urls]
    images = await asyncio.gather(*tasks)

    files = []
    for i, image_data in enumerate(images):
        if image_data:
            file_name = f"slideshow_image_{i+1}.jpg"
            files.append(disnake.File(fp=image_data, filename=file_name))
        else:
            return None, f"Failed to download image #{i+1}."

    return files, None

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
                    slideshow_urls = tiktok_response['data']['download']
                    slideshow_files, error_message = await process_slideshow(slideshow_urls, bot.http_session)
                    
                    if slideshow_files:
                        try:
                            message_content = f"{ctx.author.mention}: {caption}" if caption else f"{ctx.author.mention} used /tiktok"
                            await ctx.channel.send(content=message_content, files=slideshow_files)
                            for file in slideshow_files:
                                file.fp.close()
                        except disnake.HTTPException as e:
                            await ctx.send(f"An error occurred while uploading the slideshow: {e}", ephemeral=True)
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