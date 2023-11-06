from disnake.ext import commands
import disnake
import asyncio

class ThreadMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TARGET_CHANNEL_ID = 1100169484939038881

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if thread.parent_id == self.TARGET_CHANNEL_ID:
            # Wait a bit for messages to possibly appear in the thread
            await asyncio.sleep(2)  # wait for 1 second
            messages = await thread.history(limit=100).flatten()
            if not messages:
                print("No messages to repost.")
                return

            # Collect messages to repost
            repost_messages = []
            for message in messages[::-1]:
                content = message.content
                if message.attachments:
                    content += ' ' + ' '.join(attachment.url for attachment in message.attachments)
                if message.embeds:
                    content += ' ' + ' '.join(str(embed.to_dict()) for embed in message.embeds)

                # Format the message
                formatted_message = f"{message.author.mention}: {content}\n"
                if len(formatted_message) <= 2000:
                    repost_messages.append(formatted_message)
                else:
                    # Split long message into multiple messages
                    repost_messages.extend([formatted_message[i:i+2000] for i in range(0, len(formatted_message), 2000)])

            await thread.delete()

            # Send the collected messages
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
