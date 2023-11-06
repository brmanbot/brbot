from disnake.ext import commands
import disnake
import asyncio

class ThreadMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TARGET_CHANNEL_ID = 1082813041122496602

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if thread.parent_id == self.TARGET_CHANNEL_ID:
            await asyncio.sleep(2)
            messages = await thread.history(limit=100).flatten()
            if not messages:
                print("No messages to repost.")
                return

            repost_messages = []
            for message in messages[::-1]:
                content = message.content
                if message.attachments:
                    content += ' ' + ' '.join(attachment.url for attachment in message.attachments)
                if message.embeds:
                    content += ' ' + ' '.join(str(embed.to_dict()) for embed in message.embeds)

                formatted_message = f"{message.author.mention}: {content}\n"
                if len(formatted_message) <= 2000:
                    repost_messages.append(formatted_message)
                else:
                    repost_messages.extend([formatted_message[i:i+2000] for i in range(0, len(formatted_message), 2000)])

            await thread.delete()

            parent_channel = self.bot.get_channel(self.TARGET_CHANNEL_ID)
            if parent_channel:
                for repost_message in repost_messages:
                    try:
                        await parent_channel.send(repost_message)
                    except Exception as e:
                        print(f"Failed to send message: {e}")
            else:
                print(f"Could not find the parent channel with ID {self.TARGET_CHANNEL_ID}")

def setup(bot):
    bot.add_cog(ThreadMonitor(bot))
