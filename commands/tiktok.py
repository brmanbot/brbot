import disnake
from disnake.ext import commands
import requests
import asyncio
from utils import shorten_url

def setup(bot):
    @bot.slash_command(
        name="tiktok",
        description="Provide a shortened direct link to a TikTok video.",
        options=[
            disnake.Option(
                "url",
                "Enter the URL of the TikTok video.",
                type=disnake.OptionType.string,
                required=True
            )
        ]
    )
    async def downloadtiktok(ctx, url: str):
        await ctx.response.defer()

        if url.startswith("https://vm.tiktok.com/") or url.startswith("http://vm.tiktok.com/"):
            resolved_url = requests.head(url, allow_redirects=True).url
        else:
            resolved_url = url

        api_url = "https://api.tik.fail/api/grab"
        headers = {"User-Agent": "MyTikTokBot"}
        data = {"url": resolved_url}
        response = requests.post(api_url, headers=headers, data=data)

        if response.status_code == 200:
            json_response = response.json()
            if json_response.get("success") and "data" in json_response and "download" in json_response["data"]:
                video_link = json_response["data"]["download"]["video"].get("NoWM", {}).get("url")
                
                if video_link:
                    shortened_link = await shorten_url(video_link)
                    if shortened_link:
                        await ctx.edit_original_response(content=f"{shortened_link}")
                    else:
                        await ctx.edit_original_response(content="Failed to shorten the video link.")
                else:
                    await ctx.edit_original_response(content="No 'No Watermark' video quality found.")
            else:
                await ctx.edit_original_response(content="Failed to get video link from the response.")
        else:
            await ctx.edit_original_response(content=f"Error fetching video link. Status Code: {response.status_code}")