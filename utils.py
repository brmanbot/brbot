import asyncio
import datetime
import json
import os
import time
import aiohttp
import aiosqlite
import pyshorteners
import disnake

from disnake.ext import commands
from disnake import ApplicationCommandInteraction
from disnake.ext.commands import InteractionBot
import requests

from config import BOSSMANROLE_ID, ALLOWED_USER_ID, INTENTS, get_cooldown, update_cooldown
from database import fisher_yates_shuffle
from video_manager import VideoManager

print("Utils imported...")

class CustomBot(commands.InteractionBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cooldown = None
        self.update_cooldown()
        self.video_manager = None
        self.active_videos = {}
        self.http_session = aiohttp.ClientSession()

    @property
    def cooldown(self):
        self.update_cooldown()
        return self._cooldown

    def update_cooldown(self):
        self._cooldown = get_cooldown()

    async def close(self):
        await self.http_session.close()
        await super().close()

bot = CustomBot(intents=INTENTS)

async def setup_video_manager(bot):
    bot.video_manager = await VideoManager.create(bot)
    
setup_data = {"message_id": 0, "channel_id": 0, "target_channel_id": 0}


# Utility Functions
async def shorten_url(url: str) -> str:
    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(None, requests.get, 'https://da.gd/shorten?r=1&url={}'.format(url))
        response.raise_for_status()
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        print(f"Error shortening URL: {e}")
        return None
                                        

async def autocomp_colours(inter: ApplicationCommandInteraction, user_input: str):
    colours = ["Green", "Red", "Yellow"]
    suggestions = [colour for colour in colours if colour.startswith(user_input.lower())]
    return suggestions


async def autocomp_video_names(inter: ApplicationCommandInteraction, user_input: str):
    async with aiosqlite.connect("videos.db") as db:
        async with db.execute("SELECT name FROM videos WHERE name LIKE ? ORDER BY name ASC LIMIT 25", (f"%{user_input}%",)) as cursor:
            results = await cursor.fetchall()
            suggestions = [result[0] for result in results]
            return suggestions


async def has_role_check(ctx):
    if not ctx.author:
        return False
    user_roles = ctx.author.roles
    user_id = ctx.author.id
    is_bossman = disnake.utils.get(user_roles, id=BOSSMANROLE_ID) is not None
    is_allowed_user = user_id == ALLOWED_USER_ID
    return is_bossman or is_allowed_user


# Setup Data Management Functions
def load_setup_data(guild_id):
    guild_id = str(guild_id)
    if not os.path.exists("config_data.json"):
        return 0, 0, 0

    with open("config_data.json", "r") as f:
        data = json.load(f)

    if guild_id in data:
        return data[guild_id]["message_id"], data[guild_id]["channel_id"], data[guild_id]["target_channel_id"]
    else:
        return 0, 0, 0


def store_setup_data(guild_id, message_id, channel_id, target_channel_id):
    guild_id = str(guild_id)
    if not os.path.exists("config_data.json"):
        data = {}
    else:
        with open("config_data.json", "r") as f:
            data = json.load(f)

    data[guild_id] = {
        "message_id": message_id,
        "channel_id": channel_id,
        "target_channel_id": target_channel_id
    }

    with open("config_data.json", "w") as f:
        json.dump(data, f, indent=4)

    return None


# Role Timestamps Management Functions
def load_role_timestamps(guild_id):
    guild_id = str(guild_id)
    if os.path.exists("role_timestamps.json"):
        with open("role_timestamps.json", "r") as file:
            data = json.load(file)
        if guild_id in data:
            return data[guild_id]
    return {}


def store_role_timestamps(guild_id, user_id, removal_timestamp, role_id):
    guild_id = str(guild_id)
    user_id = str(user_id)
    role_id = str(role_id)
    with open("role_timestamps.json", "r") as file:
        data = json.load(file)
    if guild_id not in data:
        data[guild_id] = {}
    data[guild_id][user_id] = {"removal_timestamp": removal_timestamp, "role_id": role_id}
    with open("role_timestamps.json", "w") as file:
        json.dump(data, file)


def update_guild_role_timestamps(guild_id, role_timestamps):
    guild_id = str(guild_id)
    with open("role_timestamps.json", "r") as file:
        data = json.load(file)
    data[guild_id] = role_timestamps
    with open("role_timestamps.json", "w") as file:
        json.dump(data, file)


def load_all_role_timestamps():
    if os.path.exists("role_timestamps.json"):
        with open("role_timestamps.json", "r") as file:
            data = json.load(file)
        return data
    return {}


# Role Management Functions
async def schedule_role_removals(bot):
    role_removal_data = load_all_role_timestamps()
    for guild in bot.guilds:
        if str(guild.id) in role_removal_data:
            user_ids = list(role_removal_data[str(guild.id)].keys())
            for user_id in user_ids:
                user_data = role_removal_data[str(guild.id)][user_id]
                user_id = int(user_id)
                removal_timestamp = user_data['removal_timestamp']
                role_id = int(user_data['role_id'])
                removal_time = datetime.datetime.fromtimestamp(removal_timestamp)

                if removal_time <= datetime.datetime.now():
                    user = await guild.fetch_member(user_id)
                    role = guild.get_role(role_id)
                    if role in user.roles:
                        await user.remove_roles(role)

                    del role_removal_data[str(guild.id)][str(user_id)]
                    update_guild_role_timestamps(guild.id, role_removal_data[str(guild.id)])
                else:
                    async def remove_role_at_time():
                        await disnake.utils.sleep_until(removal_time)
                        user = await guild.fetch_member(user_id)
                        role = guild.get_role(role_id)
                        if role in user.roles:
                            await user.remove_roles(role)

                        del role_removal_data[str(guild.id)][str(user_id)]
                        update_guild_role_timestamps(guild.id, role_removal_data[str(guild.id)])

                    bot.loop.create_task(remove_role_at_time())


async def remove_role_after_duration(user, role_id, duration):
    await asyncio.sleep(duration)
    await remove_role(user, role_id)


async def remove_role(user, role_id):
    role = user.guild.get_role(role_id)
    if role in user.roles:
        await user.remove_roles(role)


async def remove_role_later(member, role_id, duration):
    removal_time = datetime.datetime.now() + datetime.timedelta(seconds=duration)
    store_role_timestamps(member.guild.id, member.id, removal_time.timestamp(), role_id)

    await disnake.utils.sleep_until(removal_time)
    role = member.guild.get_role(role_id)
    updated_member = await member.guild.fetch_member(member.id)
    if role in updated_member.roles:
        await updated_member.remove_roles(role)

    role_timestamps = load_role_timestamps(updated_member.guild.id)

    if str(updated_member.id) in role_timestamps:
        del role_timestamps[str(updated_member.id)]

    with open("role_timestamps.json", "w") as file:
        json.dump(role_timestamps, file)