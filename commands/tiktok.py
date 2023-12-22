import disnake
from disnake.ext import commands
import aiohttp

async def resolve_short_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.head(url, allow_redirects=True) as response:
            return str(response.url)

async def fetch_tiktok_content(session, url):
    async with session.post("https://api.tik.fail/api/grab", headers={"User-Agent": "MyTikTokBot"}, data={"url": url}) as response:
        if response.status == 200:
            return await response.json()
        else:
            return None

def setup(bot):
    @bot.slash_command(
        name="tiktok",
        description="Provide links to TikTok video or gallery images.",
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
        await ctx.response.defer()

        if url.startswith("https://vm.tiktok.com/") or url.startswith("http://vm.tiktok.com/"):
            resolved_url = await resolve_short_url(url)
        else:
            resolved_url = url

        async with aiohttp.ClientSession() as session:
            tiktok_response = await fetch_tiktok_content(session, resolved_url)
            if tiktok_response and tiktok_response.get("success"):
                # Handle gallery (list of image URLs)
                if isinstance(tiktok_response["data"].get("download"), list):
                    image_links = tiktok_response["data"]["download"]
                    formatted_links = [f"[Image {index + 1}]({link})" for index, link in enumerate(image_links)]
                    await ctx.edit_original_response(content="\n".join(formatted_links))
                # Handle video
                elif "video" in tiktok_response["data"].get("download", {}):
                    video_link = tiktok_response["data"]["download"]["video"].get("NoWM", {}).get("url")
                    if video_link:
                        await ctx.edit_original_response(content=f"[Video]({video_link})")
                    else:
                        await ctx.edit_original_response(content="No video found.")
                else:
                    await ctx.edit_original_response(content="Unsupported TikTok content.")
            else:
                await ctx.edit_original_response(content="Failed to fetch TikTok content.")
