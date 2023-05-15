import asyncio
import datetime
import json
import os
import time
import aiosqlite
import pyshorteners
import disnake

from disnake.ext import commands
from disnake import ApplicationCommandInteraction, NotFound

from config import BOSSMANROLE_ID, ALLOWED_USER_ID, INTENTS
from database import fisher_yates_shuffle


bot = commands.Bot(command_prefix=disnake.ext.commands.when_mentioned, intents=INTENTS)


class VideoManager:
    def __init__(self):
        self.video_lists = {}
        self.last_reset = {}
        self.played_videos = {}
        self.load_data()
        self.db_path = "videos.db"
        self.data = {"green": [], "red": [], "yellow": []}

    def load_data(self):
        try:
            with open("video_data.json", "r") as f:
                data = json.load(f)
                self.video_lists = data.get("video_lists", {})
                self.last_reset = data.get("last_reset", {})
                self.played_videos = data.get("played_videos", {})
        except Exception as e:
            print(f"Error loading data from file: {e}")

    def save_data(self):
        with open("video_data.json", "w") as f:
            data = {
                "video_lists": self.video_lists,
                "last_reset": self.last_reset,
                "played_videos": self.played_videos,
            }
            json.dump(data, f)

    async def remove_video(self, identifier, identifier_type):
        removed_url = None
        removed_name = None

        async with aiosqlite.connect("videos.db") as db:
            for color in ["green", "red", "yellow"]:
                query = f"SELECT * FROM videos WHERE {identifier_type} = ? AND color = ?"
                values = (identifier, color)
                async with db.execute(query, values) as cursor:
                    result = await cursor.fetchone()
                    if result is not None:
                        removed_name = result[1]
                        removed_url = result[2]
                        await db.execute(f"DELETE FROM videos WHERE {identifier_type} = ? AND color = ?", (identifier, color))
                        await db.commit()
                        break

        if removed_url is not None and removed_name is not None:
            for color in ["green", "red", "yellow"]:
                if color not in self.video_lists:
                    self.video_lists[color] = []
                if removed_url in self.video_lists[color]:
                    self.video_lists[color].remove(removed_url)

            if removed_url in self.played_videos:
                del self.played_videos[removed_url]

            self.save_data()

        return removed_url, removed_name

    async def get_available_videos(self, colors):
        current_time = time.time()
        available_videos = []

        async with aiosqlite.connect("videos.db") as db:
            for c in colors:
                if not self.video_lists.get(c) or (current_time - self.last_reset.get(c, 0) > 129600):
                    query = "SELECT url FROM videos WHERE color = ?"
                    values = (c,)
                    async with db.execute(query, values) as cursor:
                        results = await cursor.fetchall()

                    self.video_lists[c] = [url for url, in results]
                    self.last_reset[c] = current_time
                    fisher_yates_shuffle(self.video_lists[c])

                available_videos.extend(self.video_lists[c])

        return available_videos
    
    async def get_video_url(self, name: str):
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT url FROM videos WHERE name = ?"
            values = (name,)
            async with db.execute(query, values) as cursor:
                result = await cursor.fetchone()

            if result is not None:
                return result[0]
            else:
                return None

    async def get_video_color(self, name: str):
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT color FROM videos WHERE name = ?"
            values = (name,)
            async with db.execute(query, values) as cursor:
                result = await cursor.fetchone()

            if result is not None:
                return result[0]
            else:
                return None
            
    async def change_video_color(self, name: str, new_color: str):
        old_color = await self.get_video_color(name)
        url = await self.get_video_url(name)
        if old_color is not None and url is not None:
            async with aiosqlite.connect(self.db_path) as db:
                query = "UPDATE videos SET color = ? WHERE name = ?"
                values = (new_color, name)
                await db.execute(query, values)
                await db.commit()

            if old_color in self.video_lists:
                if url in self.video_lists[old_color]:
                    self.video_lists[old_color].remove(url)

            if new_color in self.video_lists:
                self.video_lists[new_color].append(url)
            else:
                self.video_lists[new_color] = [url]

            self.save_data()


async def shorten_url(url: str) -> str:
    s = pyshorteners.Shortener()
    try:
        return s.tinyurl.short(url)
    except pyshorteners.exceptions.ShorteningErrorException:
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


setup_data = {"message_id": 0, "channel_id": 0, "target_channel_id": 0}