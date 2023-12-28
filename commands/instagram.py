import aiohttp
import disnake
from disnake.ext import commands
import re
import io
from private_config import RAPID_API_KEY

def setup(bot):
    @bot.slash_command(
        name="insta",
        description="Process Instagram Reels for easy viewing.",
        options=[
            disnake.Option(
                name="url1",
                description="First Instagram Reel URL.",
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
                description=f"Reel #{i}.",
                type=disnake.OptionType.string,
                required=False
            ) for i in range(2, 11)
        ]
    )
    async def downloadreel(ctx, url1, caption=None, **urls):
        await ctx.send("Processing your request...", ephemeral=True)
        first_message = True
        urls = {'url1': url1, **urls}

        async with aiohttp.ClientSession() as session:
            for url_key in sorted(urls.keys()):
                url = urls[url_key]
                if not url:
                    continue

                if not re.match(r'https?://www\.instagram\.com/(p|reel)/[a-zA-Z0-9-_]+', url):
                    await ctx.send(f"Invalid Instagram URL: {url}")
                    continue

                api_url = "https://instagram-api32.p.rapidapi.com/"
                querystring = {"url": url}
                headers = {
                    "X-RapidAPI-Key": RAPID_API_KEY,
                    "X-RapidAPI-Host": "instagram-api32.p.rapidapi.com"
                }

                async with session.get(api_url, headers=headers, params=querystring) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, dict) and "error" in data:
                            error_message = data["error"]
                            await ctx.send(f"Error: {error_message}", ephemeral=True)
                        elif isinstance(data, dict) and "medias" in data:
                            medias = data["medias"]
                            if medias and isinstance(medias, list):
                                video_url = medias[0].get("url")
                                if video_url:
                                    async with session.get(video_url) as video_response:
                                        if video_response.status == 200:
                                            video_content = await video_response.read()
                                            video_buffer = io.BytesIO(video_content)
                                            video_buffer.seek(0)

                                            if first_message:
                                                message_content = (
                                                    f"{ctx.author.mention}: {caption}" 
                                                    if caption 
                                                    else f"{ctx.author.mention} used /insta"
                                                )
                                                first_message = False
                                            else:
                                                message_content = None
                                            file = disnake.File(fp=video_buffer, filename="instagram_reel.mp4")
                                            await ctx.channel.send(content=message_content, file=file)
                                        else:
                                            await ctx.send(
                                                "Failed to download the reel from the provided URL.",
                                                ephemeral=True
                                            )
                                else:
                                    await ctx.send(
                                        "No video URL was found in the API response.",
                                        ephemeral=True
                                    )
                            else:
                                await ctx.send(
                                    "The 'medias' key in the API response is not in the expected format.",
                                    ephemeral=True
                                )
                        else:
                            await ctx.send(
                                "The API response is not in the expected format.",
                                ephemeral=True
                            )
                    else:
                        await ctx.send(
                            f"Failed to communicate with the API. Status code: {response.status}",
                            ephemeral=True
                        )
