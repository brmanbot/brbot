import disnake
from disnake.ext import commands
import aiohttp
import io

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
        description="Download and share multiple TikTok videos directly in the channel",
        options=[
            disnake.Option(
                "url1",
                "Enter the URL of the first TikTok content.",
                type=disnake.OptionType.string,
                required=True
            )
        ] + [
            disnake.Option(
                f"url{i}",
                f"Enter the URL of TikTok content #{i}.",
                type=disnake.OptionType.string,
                required=False
            ) for i in range(2, 11)
        ]
    )
    async def downloadtiktok(ctx, **urls):
        await ctx.send("Processing your request...", ephemeral=True)
        first_message = True

        for url_key in sorted(urls.keys()):
            original_url = urls[url_key]
            if not original_url:
                continue

            resolved_url = await resolve_short_url(original_url) if original_url.startswith("https://vm.tiktok.com/") else original_url

            async with aiohttp.ClientSession() as session:
                tiktok_response = await fetch_tiktok_content(session, resolved_url)
                if tiktok_response and tiktok_response.get("success"):
                    video_url = tiktok_response["data"]["download"]["video"].get("NoWM", {}).get("url")
                    video_data = await download_video(video_url)
                    if video_data:
                        try:
                            if first_message:
                                message_content = f"{ctx.author.mention} used /tiktok"
                                first_message = False
                            else:
                                message_content = None
                            file = disnake.File(fp=video_data, filename="tiktok_video.mp4")
                            await ctx.channel.send(content=message_content, file=file)
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