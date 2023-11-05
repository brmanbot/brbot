from disnake.ext import commands
import disnake

class ThreadMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TARGET_USER_ID = 1081004946872352958  # The ID of the specific user
        self.TARGET_CHANNEL_ID = 1082813041122496602  # The ID of the specific channel

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if thread.parent_id == self.TARGET_CHANNEL_ID and thread.owner_id == self.TARGET_USER_ID:
            await disnake.utils.sleep_until(thread.created_at + disnake.timedelta(seconds=1))

            messages = await thread.history(limit=100).flatten()

            await thread.delete()

            parent_channel = self.bot.get_channel(self.TARGET_CHANNEL_ID)
            if parent_channel:
                repost_message = "Messages reposted from a thread created by the specified user:\n"
                for message in messages[::-1]:
                    repost_message += f"{message.author.display_name}: {message.content}\n"
                    
                if len(repost_message) > 2000:
                    chunks = [repost_message[i:i+2000] for i in range(0, len(repost_message), 2000)]
                    for chunk in chunks:
                        await parent_channel.send(chunk)
                else:
                    await parent_channel.send(repost_message)

def setup(bot):
    bot.add_cog(ThreadMonitor(bot))