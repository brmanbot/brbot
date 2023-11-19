import json
import asyncio
import datetime
from disnake.ext import commands
import disnake
from config import GUILD_IDS
from utils import has_role_check

class AutoDelete(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.config_data = self.load_config_data()
        self.deletion_tasks = {}
        self.load_and_schedule_deletions()

    def load_config_data(self):
        try:
            with open('config_data.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            default_data = {"auto_delete": {}}
            with open('config_data.json', 'w') as file:
                json.dump(default_data, file, indent=4)
            return default_data

    def save_config_data(self):
        with open('config_data.json', 'w') as file:
            json.dump(self.config_data, file, indent=4)

    def load_and_schedule_deletions(self):
        try:
            with open('deletion_tasks.json', 'r') as file:
                deletion_data = json.load(file)
            for message_id, info in deletion_data.items():
                channel_id = info['channel_id']
                deletion_time = datetime.datetime.fromisoformat(info['deletion_time'])
                delay = (deletion_time - datetime.datetime.utcnow()).total_seconds()
                if delay > 0:
                    asyncio.create_task(self.delete_message_after_delay(message_id, channel_id, delay))
        except FileNotFoundError:
            pass

    def save_deletion_task(self, message_id, channel_id, deletion_time):
        try:
            with open('deletion_tasks.json', 'r') as file:
                deletion_data = json.load(file)
        except FileNotFoundError:
            deletion_data = {}

        deletion_data[message_id] = {
            "channel_id": channel_id,
            "deletion_time": deletion_time.isoformat()
        }
        
        with open('deletion_tasks.json', 'w') as file:
            json.dump(deletion_data, file, indent=4)

    async def delete_message_after_delay(self, message_id, channel_id, delay):
        await asyncio.sleep(delay)
        channel = self.bot.get_channel(int(channel_id))
        if channel:
            retry_attempts = 0
            max_retries = 3
            while retry_attempts < max_retries:
                try:
                    message = await channel.fetch_message(int(message_id))
                    await message.delete()
                    break
                except disnake.NotFound:
                    break
                except disnake.HTTPException as e:
                    if e.status == 429:
                        retry_after = e.headers.get('Retry-After')
                        if retry_after:
                            await asyncio.sleep(float(retry_after))
                            retry_attempts += 1
                    else:
                        break
                finally:
                    self.remove_deletion_task(str(message_id))

    def remove_deletion_task(self, message_id):
        try:
            with open('deletion_tasks.json', 'r') as file:
                deletion_data = json.load(file)
            deletion_data.pop(message_id, None)
            with open('deletion_tasks.json', 'w') as file:
                json.dump(deletion_data, file, indent=4)
        except FileNotFoundError:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            return

        channel_id = str(message.channel.id)
        if channel_id in self.config_data.get("auto_delete", {}):
            delay = self.config_data["auto_delete"][channel_id]
            deletion_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=delay)
            task = asyncio.create_task(self.delete_message_after_delay(str(message.id), channel_id, delay))
            self.deletion_tasks[(channel_id, str(message.id))] = task
            self.save_deletion_task(str(message.id), channel_id, deletion_time)

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
        self.config_data['auto_delete'][str(channel.id)] = delay
        self.save_config_data()

        await ctx.send(f"Messages in {channel.mention} will be automatically deleted after {value} {unit}.", ephemeral=True)

    @autodelete.sub_command(
        name='remove',
        description='Remove a channel from auto-delete messages'
    )
    async def autodelete_remove(self, ctx, channel: disnake.TextChannel):
        if not await has_role_check(ctx):
            await ctx.send("You don't have permission to use this command.", ephemeral=True)
            return

        if str(channel.id) in self.config_data.get('auto_delete', {}):
            del self.config_data['auto_delete'][str(channel.id)]
            self.save_config_data()
            await ctx.send(f"Channel {channel.mention} has been removed from auto-delete.", ephemeral=True)
        else:
            await ctx.send(f"Channel {channel.mention} is not in the auto-delete list.", ephemeral=True)

def setup(bot):
    bot.add_cog(AutoDelete(bot))