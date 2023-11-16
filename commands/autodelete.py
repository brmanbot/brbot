import json
import asyncio
import datetime
from disnake.ext import commands
import disnake
import pytz
from config import GUILD_IDS
from utils import has_role_check

class AutoDelete(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        asyncio.create_task(self.initialize_auto_delete())

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

    @commands.slash_command(
        name='autodelete',
        description='Manage auto-deletion of messages in a channel',
        guild_ids=GUILD_IDS
    )
    async def autodelete(self, ctx):
        pass

    @autodelete.sub_command(
        name='add',
        description='Add a channel to auto-delete messages after a specified time',
        options=[
            disnake.Option(
                "channel",
                "Select the channel for auto-deletion",
                type=disnake.OptionType.channel,
                required=True
            ),
            disnake.Option(
                "value",
                "The value to set the auto-delete time to",
                type=disnake.OptionType.integer,
                required=True
            ),
            disnake.Option(
                "unit",
                "The unit of time for auto-deletion",
                type=disnake.OptionType.string,
                required=True,
                choices=[
                    disnake.OptionChoice("Seconds", "seconds"),
                    disnake.OptionChoice("Minutes", "minutes"),
                    disnake.OptionChoice("Hours", "hours"),
                    disnake.OptionChoice("Days", "days"),
                    disnake.OptionChoice("Weeks", "weeks")
                ]
            )
        ]
    )
    async def autodelete_add(self, ctx, channel: disnake.TextChannel, value: int, unit: str):
        if not await has_role_check(ctx):
            await ctx.send("You don't have permission to use this command.", ephemeral=True)
            return

        time_converters = {
            "seconds": 1,
            "minutes": 60,
            "hours": 3600,
            "days": 86400,
            "weeks": 604800
        }
        delay = value * time_converters[unit]

        config_data = self.get_config_data()
        config_data.setdefault('auto_delete', {})[str(channel.id)] = delay
        self.update_config_data(config_data)

        await ctx.send(f"Messages in {channel.mention} will be automatically deleted after {value} {unit}.", ephemeral=True)
        asyncio.create_task(self.monitor_channel(channel.id, delay))

    @autodelete.sub_command(
        name='remove',
        description='Remove a channel from auto-delete messages'
    )
    async def autodelete_remove(self, ctx, channel: disnake.TextChannel):
        if not await has_role_check(ctx):
            await ctx.send("You don't have permission to use this command.", ephemeral=True)
            return

        config_data = self.get_config_data()
        if str(channel.id) in config_data.get('auto_delete', {}):
            del config_data['auto_delete'][str(channel.id)]
            self.update_config_data(config_data)
            await ctx.send(f"Channel {channel.mention} has been removed from auto-delete.", ephemeral=True)
        else:
            await ctx.send(f"Channel {channel.mention} is not in the auto-delete list.", ephemeral=True)

    async def monitor_channel(self, channel_id, delay):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        while True:
            now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
            try:
                messages = await channel.history(limit=100).flatten()
                for message in messages:
                    if message.pinned:
                        continue

                    time_diff = (now - message.created_at).total_seconds()
                    if time_diff > delay:
                        try:
                            await message.delete()
                        except disnake.NotFound:
                            continue
            except disnake.Forbidden:
                print(f"Missing permissions to read history or delete messages in channel {channel_id}")
                return
            await asyncio.sleep(delay)

    async def initialize_auto_delete(self):
        await self.bot.wait_until_ready()
        config_data = self.get_config_data()
        auto_delete_config = config_data.get('auto_delete', {})
        for channel_id, time in auto_delete_config.items():
            asyncio.create_task(self.monitor_channel(int(channel_id), time))

def setup(bot):
    bot.add_cog(AutoDelete(bot))
