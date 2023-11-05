from disnake.ext import commands
import disnake
from datetime import timedelta

class ThreadMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TARGET_CHANNEL_ID = 1082813041122496602

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if thread.parent_id == self.TARGET_CHANNEL_ID:
            await disnake.utils.sleep_until(thread.created_at + timedelta(seconds=0.5))
            messages = await thread.history(limit=100).flatten()
            await thread.delete()
            parent_channel = self.bot.get_channel(self.TARGET_CHANNEL_ID)
            if parent_channel:
                repost_message = "Messages reposted from a thread:\n"
                for message in messages[::-1]:
                    repost_message += f"{message.author.mention}: {message.content}\n"
                    if len(repost_message) > 1900:
                        await parent_channel.send(repost_message)
                        repost_message = ""
                if repost_message:
                    await parent_channel.send(repost_message)

def setup(bot):
    bot.add_cog(ThreadMonitor(bot))