import json
import time
import aiosqlite
import pyshorteners
import disnake

from disnake.ext import commands
from disnake import ApplicationCommandInteraction

from config import BOSSMANROLE_ID, ALLOWED_USER_ID, INTENTS
from database import fisher_yates_shuffle


bot = commands.Bot(command_prefix=disnake.ext.commands.when_mentioned, intents=INTENTS)


class VideoManager:
    def __init__(self):
        self.video_lists = {}
        self.last_reset = {}
        self.played_videos = {}
        self.load_data()

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
            with open("video_data.json", "r") as file:
                data = json.load(file)
                video_lists = data.get("video_lists", {})
                played_videos = data.get("played_videos", {})

            for color in ["green", "red", "yellow"]:
                if color not in video_lists:
                    video_lists[color] = []
                if removed_url in video_lists[color]:
                    video_lists[color].remove(removed_url)

            if removed_url in played_videos:
                del played_videos[removed_url]

            with open("video_data.json", "w") as file:
                json.dump({"video_lists": video_lists, "played_videos": played_videos}, file, indent=4)

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

