import json
import asyncio
from disnake.ext import commands
import disnake
from config import GUILD_IDS
from utils import has_role_check

class AutoDelete(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.deletion_tasks = {}
        self.config_data = self.load_config_data()

    def load_config_data(self):
        try:
            with open('config_data.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            with open('config_data.json', 'w') as file:
                json.dump({"auto_delete": {}}, file, indent=4)
            return {"auto_delete": {}}

    def save_config_data(self):
        with open('config_data.json', 'w') as file:
            json.dump(self.config_data, file, indent=4)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or message.author.bot:
            return

        channel_id = str(message.channel.id)
        if channel_id in self.config_data.get("auto_delete", {}):
            delay = self.config_data["auto_delete"][channel_id]
            task = asyncio.create_task(self.delete_message_after_delay(message, delay))
            self.deletion_tasks[(channel_id, message.id)] = task

    async def delete_message_after_delay(self, message, delay):
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except disnake.NotFound:
            pass
        finally:
            self.deletion_tasks.pop((str(message.channel.id), message.id), None)

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