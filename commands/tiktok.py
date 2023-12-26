import disnake
from disnake.ext import commands
import aiohttp
import io
import re

http_session = aiohttp.ClientSession()


async def resolve_short_url(url):
    async with http_session.head(url, allow_redirects=True) as response:
        return str(response.url)


async def fetch_tiktok_content(url):
    async with http_session.post(
        "https://api.tik.fail/api/grab",
        headers={"User-Agent": "MyTikTokBot"},
        data={"url": url}
    ) as response:
        if response.status == 200:
            return await response.json()
        else:
            return None


async def download_video(video_url):
    async with http_session.get(video_url) as response:
        if response.status == 200:
            return io.BytesIO(await response.read())
        else:
            return None


def get_video_id_from_url(url):
    match = re.search(r'/video/(\d+)', url)
    return match.group(1) if match else None


def setup(bot):
    @bot.slash_command(
        name="tiktok",
        description="Process TikTok videos for easy viewing.",
        options=[
            disnake.Option(
                "url1",
                "First TikTok.",
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
                f"TikTok #{i}.",
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

            resolved_url = await resolve_short_url(original_url) if original_url.startswith("https://vm.tiktok.com/") else original_url

            tiktok_response = await fetch_tiktok_content(resolved_url)
            if tiktok_response and tiktok_response.get("success"):
                author_id = tiktok_response["data"]["metadata"]["AccountUserName"]
                video_id = get_video_id_from_url(tiktok_response["data"]["metadata"]["VideoURL"])
                video_url = tiktok_response["data"]["download"]["video"].get("NoWM", {}).get("url")
                video_data = await download_video(video_url)
                if video_data:
                    try:
                        file_name = f"{author_id}_{video_id}.mp4"
                        if first_message:
                            message_content = f"{ctx.author.mention}: {caption}" if caption else f"{ctx.author.mention} used /tiktok"
                            first_message = False
                        else:
                            message_content = None
                        file = disnake.File(fp=video_data, filename=file_name)
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