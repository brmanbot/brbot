import disnake
from disnake.ext import commands
from datetime import timedelta
import logging

# Set up basic logging to print to stderr
logging.basicConfig(level=logging.INFO)

class ThreadMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TARGET_CHANNEL_ID = 1100169484939038881

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        try:
            if thread.parent_id == self.TARGET_CHANNEL_ID:
                await disnake.utils.sleep_until(thread.created_at + timedelta(seconds=1))
                messages = await thread.history(limit=100).flatten()
                
                # Debugging: Print messages
                logging.info(f"Fetched {len(messages)} messages from the thread.")

                # Temporarily comment out deletion for testing
                # await thread.delete()

                parent_channel = self.bot.get_channel(self.TARGET_CHANNEL_ID)
                if parent_channel:
                    repost_message = "Messages reposted from a thread:\n"
                    for message in messages[::-1]:
                        repost_message += f"{message.author.mention}: {message.content}\n"
                        # Check if the message length is over the Discord limit and send
                        if len(repost_message) > 1900:
                            await parent_channel.send(repost_message)
                            repost_message = ""
                    # Send any remaining content
                    if repost_message:
                        await parent_channel.send(repost_message)
                else:
                    logging.error(f"Could not find the parent channel with ID {self.TARGET_CHANNEL_ID}")
        except Exception as e:
            logging.exception("An error occurred in on_thread_create:")
    
    # Manual command to test functionality
    @commands.command()
    async def testrepost(self, ctx, thread_id: int):
        thread = ctx.guild.get_thread(thread_id)
        if thread:
            messages = await thread.history(limit=100).flatten()
            for message in messages:
                await ctx.send(f"{message.author.mention}: {message.content}")

def setup(bot):
    bot.add_cog(ThreadMonitor(bot))
