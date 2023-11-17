import json
import asyncio
from disnake.ext import commands
import disnake
from config import GUILD_IDS
from utils import has_role_check

class ThreadMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_channel_ids = self.load_target_channels()

    def load_target_channels(self):
        config_data = self.get_config_data()
        return config_data.get('target_channels', [])

    def save_target_channels(self):
        config_data = self.get_config_data()
        config_data['target_channels'] = self.target_channel_ids
        self.update_config_data(config_data)

    def get_config_data(self):
        try:
            with open('config_data.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            print("config_data.json not found. Returning empty config.")
            return {}

    def update_config_data(self, config_data):
        try:
            with open('config_data.json', 'w') as file:
                json.dump(config_data, file, indent=4)
        except Exception as e:
            print(f"Error saving to config_data.json: {e}")

    async def format_message(self, message):
        content = message.content or ''
        content += ''.join(f' {attachment.url}' for attachment in message.attachments)
        embed_content = ''.join(self.format_embed(embed) for embed in message.embeds)
        return f"{message.author.mention}:\n{content}\n{embed_content}".strip()

    def format_embed(self, embed):
        embed_dict = embed.to_dict()
        if 'fields' in embed_dict:
            return '\n'.join(f"{field['name']}: {field['value']}" for field in embed_dict['fields'])
        return ''
    
    @commands.slash_command(
        name='threadmonitor',
        description='Manage channels for thread monitoring',
        guild_ids=GUILD_IDS
    )
    async def threadmonitor(self, ctx):
        pass

    @threadmonitor.sub_command(
        name='add',
        description='Add a channel to the thread monitor'
    )
    async def add_channel(self, ctx, channel: disnake.TextChannel):
        if not await has_role_check(ctx):
            await ctx.send("You don't have permission to use this command.", ephemeral=True)
            return

        channel_id = channel.id
        if channel_id not in self.target_channel_ids:
            self.target_channel_ids.append(channel_id)
            self.save_target_channels()
            await ctx.send(f"Channel {channel.mention} added to the thread monitor.", ephemeral=True)
        else:
            await ctx.send(f"Channel {channel.mention} is already in the thread monitor.", ephemeral=True)

    @threadmonitor.sub_command(
        name='remove',
        description='Remove a channel from the thread monitor'
    )
    async def remove_channel(self, ctx, channel: disnake.TextChannel):
        if not await has_role_check(ctx):
            await ctx.send("You don't have permission to use this command.", ephemeral=True)
            return

        channel_id = channel.id
        if channel_id in self.target_channel_ids:
            self.target_channel_ids.remove(channel_id)
            self.save_target_channels()
            await ctx.send(f"Channel {channel.mention} removed from the thread monitor.", ephemeral=True)
        else:
            await ctx.send(f"Channel {channel.mention} is not currently in the thread monitor.", ephemeral=True)

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if thread.parent_id in self.target_channel_ids:
            await asyncio.sleep(1.5)
            messages = await thread.history(limit=100).flatten()
            if not messages:
                print("No messages to repost.")
                return

            repost_messages = []
            for message in messages[::-1]:
                formatted_message = await self.format_message(message)
                if formatted_message:
                    repost_messages.extend([formatted_message[i:i+2000] for i in range(0, len(formatted_message), 2000)])

            await thread.delete()

            parent_channel = self.bot.get_channel(thread.parent_id)
            if parent_channel:
                for repost_message in repost_messages:
                    try:
                        await parent_channel.send(repost_message)
                    except Exception as e:
                        print(f"Failed to send message: {e}")
            else:
                print(f"Could not find the parent channel with ID {thread.parent_id}")

def setup(bot):
    bot.add_cog(ThreadMonitor(bot))