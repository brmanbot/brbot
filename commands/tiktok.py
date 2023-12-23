import disnake
from disnake.ext import commands
import aiohttp
import io
from utils import shorten_url
from private_config import TIKTOK_ARCHIVE_CHANNEL

async def resolve_short_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.head(url, allow_redirects=True) as response:
            return str(response.url)

async def fetch_tiktok_content(session, url):
    async with session.post(
        "https://api.tik.fail/api/grab",
        headers={"User-Agent": "MyTikTokBot"},
        data={"url": url}
    ) as response:
        if response.status == 200:
            return await response.json()
        else:
            return None

async def download_video(video_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(video_url) as response:
            if response.status == 200:
                return io.BytesIO(await response.read())
            else:
                return None

def setup(bot):
    @bot.slash_command(
        name="tiktok",
        description="Archive and process TikTok's for easy viewing",
        options=[
            disnake.Option(
                "url",
                "Enter the URL of the TikTok content.",
                type=disnake.OptionType.string,
                required=True
            )
        ]
    )
    async def downloadtiktok(ctx, url: str):
        original_url = url.split(": ", 1)[1] if ": " in url else url
        await ctx.send("Processing your request...", ephemeral=True)

        resolved_url = await resolve_short_url(original_url) if original_url.startswith("https://vm.tiktok.com/") else original_url

        async with aiohttp.ClientSession() as session:
            tiktok_response = await fetch_tiktok_content(session, resolved_url)
            if tiktok_response and tiktok_response.get("success"):
                if isinstance(tiktok_response["data"].get("download"), list):
                    image_links = tiktok_response["data"]["download"]
                    formatted_links = [f"[Image {index + 1}]({link})" for index, link in enumerate(image_links)]
                    await ctx.channel.send("\n".join(formatted_links))
                else:
                    video_url = tiktok_response["data"]["download"]["video"].get("NoWM", {}).get("url")
                    video_data = await download_video(video_url)
                    if video_data:
                        upload_channel = bot.get_channel(int(TIKTOK_ARCHIVE_CHANNEL))
                        if upload_channel:
                            try:
                                video_message = await upload_channel.send(
                                    file=disnake.File(fp=video_data, filename="tiktok_video.mp4")
                                )
                                video_media_url = video_message.attachments[0].url
                                shortened_url = await shorten_url(video_media_url)
                                if shortened_url:
                                    user_mention = ctx.author.mention
                                    await ctx.channel.send(f"{user_mention} used /tiktok\n{shortened_url}")
                                else:
                                    await ctx.channel.send(f"Failed to shorten the URL. Original link: {original_url}", ephemeral=True)
                            except disnake.HTTPException as e:
                                if e.status == 413:
                                    await ctx.send("The video file is too large to upload.", ephemeral=True)
                                else:
                                    await ctx.send(f"An error occurred while uploading the video: {e}", ephemeral=True)
                            except Exception as e:
                                await ctx.send(f"An unexpected error occurred: {e}", ephemeral=True)
                        else:
                            await ctx.channel.send("Invalid upload channel ID.", ephemeral=True)
                    else:
                        await ctx.channel.send(f"Failed to download the video. Original link: {original_url}", ephemeral=True)
            else:
                await ctx.followup.send(f"Failed to fetch TikTok content. Here's the original link: {original_url}", ephemeral=True)