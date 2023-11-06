from disnake.ext import commands
import disnake
from datetime import timedelta

class ThreadMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TARGET_CHANNEL_ID = 1100169484939038881

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if thread.parent_id == self.TARGET_CHANNEL_ID:
            await disnake.utils.sleep_until(thread.created_at + timedelta(seconds=1))
            messages = await thread.history(limit=100).flatten()
            if not messages:
                print("No messages to repost.")
                return

            await thread.delete()

            parent_channel = self.bot.get_channel(self.TARGET_CHANNEL_ID)
            if parent_channel:
                repost_message = "Messages reposted from a thread:\n"
                for message in messages[::-1]:
                    repost_message += f"{message.author.mention}: {message.content}\n"
                    if len(repost_message) > 1900:
                        try:
                            await parent_channel.send(repost_message)
                        except Exception as e:
                            print(f"Failed to send message: {e}")
                        repost_message = ""
                if repost_message:
                    try:
                        await parent_channel.send(repost_message)
                    except Exception as e:
                        print(f"Failed to send message: {e}")
            else:
                print(f"Could not find the parent channel with ID {self.TARGET_CHANNEL_ID}")

def setup(bot):
    bot.add_cog(ThreadMonitor(bot))
