from disnake.ext import commands
import disnake

class ThreadMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TARGET_CHANNEL_ID = 1100169484939038881

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if thread.parent_id == self.TARGET_CHANNEL_ID:
            messages = await thread.history(limit=100).flatten()
            if not messages:
                print("No messages to repost.")
                return

            await thread.delete()

            parent_channel = self.bot.get_channel(self.TARGET_CHANNEL_ID)
            if parent_channel:
                repost_message = ""
                for message in messages[::-1]:
                    content = message.content
                    if message.attachments:
                        content += '\n'.join(attachment.url for attachment in message.attachments)
                    if message.embeds:
                        content += '\n'.join(str(embed.to_dict()) for embed in message.embeds)

                    new_message = f"{message.author.mention}: {content}\n"
                    if len(repost_message) + len(new_message) > 1900:
                        # Send current message if the new message would exceed the limit
                        try:
                            await parent_channel.send(repost_message)
                        except Exception as e:
                            print(f"Failed to send message: {e}")
                        repost_message = new_message  # Start a new message with the new content
                    else:
                        repost_message += new_message

                # After loop, send any remaining content
                if repost_message:
                    try:
                        await parent_channel.send(repost_message)
                    except Exception as e:
                        print(f"Failed to send message: {e}")
            else:
                print(f"Could not find the parent channel with ID {self.TARGET_CHANNEL_ID}")

def setup(bot):
    bot.add_cog(ThreadMonitor(bot))
