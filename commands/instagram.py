import requests
import disnake
from disnake.ext import commands
import re
import io
from private_config import RAPID_API_KEY

def setup(bot):
    @bot.slash_command(
        name="insta",
        description="Process Instagram Reels and Posts for easy viewing.",
        options=[
            disnake.Option(
                name="url1",
                description="First Instagram URL.",
                type=disnake.OptionType.string,
                required=True
            ),
            disnake.Option(
                name="caption",
                description="Replace the `@user used /insta` message with your own.",
                type=disnake.OptionType.string,
                required=False
            )
        ] + [
            disnake.Option(
                name=f"url{i}",
                description=f"Instagram URL #{i}.",
                type=disnake.OptionType.string,
                required=False
            ) for i in range(2, 11)
        ]
    )
    async def downloadreel(ctx, url1, caption=None, **urls):
        await ctx.send("Processing your request...", ephemeral=True)
        first_message = True
        urls = {'url1': url1, **urls}

        for url_key in sorted(urls.keys()):
            url = urls[url_key]
            if not url:
                continue

            if not re.match(r'https?://www\.instagram\.com/([a-zA-Z0-9_.]+/)?(p|reel)/[a-zA-Z0-9-_]+', url):
                await ctx.send(f"Invalid Instagram URL: {url}", ephemeral=True)
                continue

            api_url = "https://instagram-downloader-download-instagram-videos-stories3.p.rapidapi.com/instagram/v1/get_info/"
            querystring = {"url": url}
            headers = {
                "X-RapidAPI-Key": RAPID_API_KEY,
                "X-RapidAPI-Host": "instagram-downloader-download-instagram-videos-stories3.p.rapidapi.com"
            }

            response = requests.get(api_url, headers=headers, params=querystring)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and "contents" in data:
                    for content in data["contents"]:
                        if "url" in content:
                            media_url = content["url"]
                            media_response = requests.get(media_url)
                            if media_response.status_code == 200:
                                media_content = media_response.content
                                media_buffer = io.BytesIO(media_content)
                                media_buffer.seek(0)

                                if media_url.endswith(('.mp4', '.mov')):
                                    filename = "video.mp4"
                                elif media_url.endswith(('.jpg', '.jpeg', '.png')):
                                    filename = "image.jpg"
                                else:
                                    continue 
                                
                                if first_message:
                                    message_content = (
                                        f"{ctx.author.mention}: {caption}" 
                                        if caption 
                                        else f"{ctx.author.mention} used /insta"
                                    )
                                    first_message = False
                                else:
                                    message_content = None

                                file = disnake.File(fp=media_buffer, filename=filename)
                                await ctx.channel.send(content=message_content, file=file)
                            else:
                                await ctx.send(
                                    "Failed to download media from the provided URL.",
                                    ephemeral=True
                                )
                        else:
                            await ctx.send(
                                "No media URL was found in the API response.",
                                ephemeral=True
                            )
                else:
                    await ctx.send(
                        "The API response is not in the expected format or status was not successful.",
                        ephemeral=True
                    )
            else:
                await ctx.send(
                    f"Failed to communicate with the API. Status code: {response.status_code}",
                    ephemeral=True
                )