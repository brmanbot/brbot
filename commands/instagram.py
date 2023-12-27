import disnake
from disnake.ext import commands
from instagrapi import Client
import aiohttp
import io

ig_client = Client()
http_session = aiohttp.ClientSession()

async def download_media_to_memory(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return io.BytesIO(await response.read())
            else:
                return None

def setup(bot):
    @bot.slash_command(
        name="insta",
        description="Process Instagram Reels for easy viewing.",
        options=[
            disnake.Option(
                "url1",
                "First Instagram Reel.",
                type=disnake.OptionType.string,
                required=True
            ),
            disnake.Option(
                "caption",
                "Replace the `@user used /insta` message with your own.",
                type=disnake.OptionType.string,
                required=False
            )
        ] + [
            disnake.Option(
                f"url{i}",
                f"Instagram Reel #{i}.",
                type=disnake.OptionType.string,
                required=False
            ) for i in range(2, 11)
        ]
    )
    async def downloadinstagramreel(ctx, url1, caption=None, **urls):
        await ctx.send("Processing your request...", ephemeral=True)
        first_message = True

        urls = {'url1': url1, **urls}

        for url_key in sorted(urls.keys()):
            original_url = urls[url_key]
            if not original_url:
                continue

            media_pk = ig_client.media_pk_from_url(original_url)
            reel_info = ig_client.media_info_gql(media_pk)
            if reel_info and reel_info.media_type == 2 and reel_info.product_type == 'clips':
                video_url = getattr(reel_info, 'video_url', None)
                if video_url:
                    video_data = await download_media_to_memory(str(video_url))
                    if video_data:
                        try:
                            file_name = f"{reel_info.user.username}_{reel_info.pk}.mp4"
                            if first_message:
                                message_content = f"{ctx.author.mention}: {caption}" if caption else f"{ctx.author.mention} used /insta"
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
                    await ctx.send(f"Reel video URL not found. Original link: {original_url}", ephemeral=True)
            else:
                await ctx.send(f"Failed to fetch Instagram Reel content. Here's the original link: {original_url}", ephemeral=True)