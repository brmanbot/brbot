import asyncio
import json
import os
import aiosqlite
from database import fisher_yates_shuffle, synchronize_cache_with_database
from config import MOD_LOG

COLORS = ["green", "red", "yellow"]


class VideoManager:
    def __init__(self, bot):
        self.bot = bot
        self.bot.video_lists = {}
        self.videos_info = {}
        self.last_reset = {}
        self.played_videos = {}
        self.hall_of_fame = []
        self.db_path = "videos.db"
        self.data = {"green": [], "red": [], "yellow": []}

    async def load_hall_of_fame(self):
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT * FROM videos WHERE is_hall_of_fame = 1"
            cursor = await db.execute(query)
            results = await cursor.fetchall()
            self.hall_of_fame = [result[4] for result in results]

    async def update_video_info_in_cache(self, name, **updates):
        video_name_lower = name.lower()
        video_info = self.videos_info.get(video_name_lower)

        if video_info:
            for key, value in updates.items():
                video_info[key] = value

    async def change_video_color_in_cache(self, video_name, new_color):
        video_name_lower = video_name.lower()
        video_info = self.videos_info.get(video_name_lower)
        if video_info:
            video_info['color'] = new_color

    async def add_video_to_cache(self, name, **details):
        video_name_lower = name.lower()
        default_video_details = {
            "url": "",
            "color": "",
            "original_url": "",
            "added_by": "",
            "tiktok_author_link": None,
            "tiktok_original_link": None,
            "tiktok_sound_link": None,
            "insta_original_link": None,
            "date_added": "",
            "hashtags": "",
            "is_hall_of_fame": 0,
        }

        updated_video_details = {**default_video_details, **details}

        self.videos_info[video_name_lower] = updated_video_details

    async def remove_video_from_cache(self, video_name):
        if video_name in self.videos_info:
            del self.videos_info[video_name]

    async def update_video_hashtags_in_cache(self, video_name, updated_hashtags):
        video_name_lower = video_name.lower()
        if video_name_lower in self.videos_info:
            self.videos_info[video_name_lower]['hashtags'] = updated_hashtags

    # async def print_cached_data(self):
    #     print("Cached Video Data:")
    #     for video_name, video_info in self.videos_info.items():
    #         print(f"Name: {video_name}")
    #         print(f"URL: {video_info['original_url']}")
    #         print(f"Color: {video_info.get('color', 'N/A')}")
    #         print(f"Added By: {video_info['added_by']}")
    #         print(f"Hashtags: {video_info['hashtags']}")
    #         print(
    #             f"Hall of Fame: {'Yes' if video_info['is_hall_of_fame'] else 'No'}")
    #         print("----------------------------------------------------")

    async def load_videos_info(self):
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT name, original_url, is_hall_of_fame, hashtags, added_by 
                FROM videos
            """
            async with db.execute(query) as cursor:
                results = await cursor.fetchall()

            self.videos_info = {
                result[0].lower(): {
                    "original_url": result[1],
                    "is_hall_of_fame": result[2],
                    "hashtags": result[3],
                    "added_by": result[4]
                }
                for result in results
            }

        # # Debug print
        # await self.print_cached_data()

    async def load_data(self):
        try:
            if not os.path.isfile("video_data.json"):
                await self.load_videos_info()
                await self.load_hall_of_fame()
                self.save_data()
            else:
                with open("video_data.json", "r") as f:
                    data = json.load(f)
                    self.bot.video_lists = data.get("video_lists", {})
                    self.last_reset = data.get("last_reset", {})
                    self.played_videos = data.get("played_videos", {})
                    self.hall_of_fame = data.get("hall_of_fame", [])

                for color in COLORS:
                    if color in self.bot.video_lists:
                        fisher_yates_shuffle(self.bot.video_lists[color])

        except Exception as e:
            print(f"Error loading data from file: {e}")
            raise e

    @classmethod
    async def create(cls, bot):
        video_manager = cls(bot)
        await video_manager.initialize_database()
        await video_manager.load_data()
        await synchronize_cache_with_database()
        return video_manager

    async def initialize_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("PRAGMA table_info(videos)")
            columns = await cursor.fetchall()
            if 'hashtags' not in [column[1] for column in columns]:
                await db.execute("""
                    ALTER TABLE videos
                    ADD COLUMN hashtags TEXT
                """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    url TEXT,
                    color TEXT,
                    original_url TEXT,
                    added_by TEXT,
                    tiktok_author_link TEXT,
                    tiktok_original_link TEXT,
                    tiktok_sound_link TEXT,
                    insta_original_link TEXT,
                    date_added TEXT,
                    is_hall_of_fame BOOLEAN DEFAULT 0,
                    hashtags TEXT
                )
            """)
            await db.commit()

    def save_data(self):
        try:
            with open("video_data.json", "w") as f:
                data = {
                    "video_lists": self.bot.video_lists,
                    "last_reset": self.last_reset,
                    "played_videos": self.played_videos,
                    "hall_of_fame": self.hall_of_fame
                }
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving data to file: {e}")
            raise e

    async def remove_video(self, identifier, identifier_type, MOD_LOG, deleted_by):
        removed_url = None
        removed_name = None
        added_by = None
        color_removed_from = None

        async with aiosqlite.connect(self.db_path) as db:
            for color in COLORS:
                query = f"SELECT * FROM videos WHERE {identifier_type} = ? AND color = ?"
                values = (identifier, color)
                async with db.execute(query, values) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        removed_name = result[1]
                        removed_url = result[4]
                        color_removed_from = result[3]
                        added_by = result[6]
                        await db.execute(f"DELETE FROM videos WHERE {identifier_type} = ? AND color = ?", (identifier, color))
                        await db.commit()
                        break

        if removed_url and removed_name:
            if color_removed_from in self.bot.video_lists and removed_url in self.bot.video_lists[color_removed_from]:
                self.bot.video_lists[color_removed_from].remove(removed_url)
                fisher_yates_shuffle(self.bot.video_lists[color_removed_from])

            self.played_videos.pop(removed_url, None)

            if removed_url in self.hall_of_fame:
                self.hall_of_fame.remove(removed_url)

            username_parts = added_by.split("#")
            username = username_parts[0]
            discriminator = username_parts[1] if len(
                username_parts) > 1 else None
            user = next((u for u in self.bot.users if u.name == username and (
                u.discriminator == discriminator if discriminator else True)), None)
            if user and user.id != deleted_by.id:
                channel = self.bot.get_channel(MOD_LOG)
                if channel:
                    message = f"<@{user.id}> your video `{removed_name}` has been deleted by `{deleted_by.name}` from the `{color_removed_from}` database <a:ALERT:916868273142906891>\n{removed_url}"
                    await channel.send(message)

        self.save_data()
        return removed_url, removed_name

    async def search_videos(self, phrase, identifier_type):
        matched_videos = []
        async with aiosqlite.connect(self.db_path) as db:
            for color in COLORS:
                query = f"SELECT * FROM videos WHERE {identifier_type} LIKE ? AND color = ?"
                values = (f"%{phrase}%", color)
                async with db.execute(query, values) as cursor:
                    result = await cursor.fetchall()
                    if result:
                        matched_videos.extend([video[4] for video in result])
        return matched_videos

    async def get_video_url(self, name: str):
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT original_url FROM videos WHERE name = ?"
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

            if old_color in self.bot.video_lists:
                if url in self.bot.video_lists[old_color]:
                    self.bot.video_lists[old_color].remove(url)

            if new_color in self.bot.video_lists:
                self.bot.video_lists[new_color].append(url)
            else:
                self.bot.video_lists[new_color] = [url]

            self.save_data()

    async def get_available_videos_with_cooldown(self, colors, current_time, cooldown):
        available_videos = []
        for color in colors:
            if color in self.bot.video_lists:
                filtered_videos = [video for video in self.bot.video_lists[color]
                                   if current_time - self.played_videos.get(video, 0) > cooldown]
                available_videos.extend(filtered_videos)

        fisher_yates_shuffle(available_videos)
        return available_videos

    async def _get_videos_for_color(self, color, current_time, cooldown):
        if not self.bot.video_lists.get(color) or (current_time - self.last_reset.get(color, 0) > 129600):
            query = "SELECT original_url FROM videos WHERE color = ?"
            values = (color,)
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(query, values)
                results = await cursor.fetchall()

            self.bot.video_lists[color] = [
                url["original_url"] for url in results]
            self.last_reset[color] = current_time
            fisher_yates_shuffle(self.bot.video_lists[color])

        return [video for video in self.bot.video_lists[color] if current_time - self.played_videos.get(video, 0) > cooldown]

    async def update_hall_of_fame(self, identifier: str):
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT original_url FROM videos WHERE name = ? OR original_url = ?"
            values = (identifier, identifier)
            async with db.execute(query, values) as cursor:
                result = await cursor.fetchone()

        if result is not None:
            video_url = result[0]
            if video_url not in self.hall_of_fame:
                self.hall_of_fame.append(video_url)
            self.save_data()

    async def fetch_video_info(self, url: str):
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT name, color, added_by, tiktok_author_link, tiktok_original_link,
                    tiktok_sound_link, insta_original_link, date_added, original_url,
                    is_hall_of_fame, hashtags
                FROM videos
                WHERE original_url = ?
            """
            values = (url,)
            async with db.execute(query, values) as cursor:
                result = await cursor.fetchone()
                if result:
                    columns = ["name", "color", "added_by", "tiktok_author_link", "tiktok_original_link",
                               "tiktok_sound_link", "insta_original_link", "date_added", "original_url",
                               "is_hall_of_fame", "hashtags"]
                    return dict(zip(columns, result))
                else:
                    return None

    async def video_exists(self, name, original_discord_url, tiktok_original_link, insta_original_link):
        query = """
        SELECT name, original_url, tiktok_original_link, insta_original_link 
        FROM videos 
        WHERE name = ? OR original_url = ? OR tiktok_original_link = ? OR insta_original_link = ?
        """
        params = (name, original_discord_url,
                  tiktok_original_link, insta_original_link)
        conflict_details = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    video_name, original_url, tiktok_link, insta_link = row
                    if video_name == name:
                        conflict_details.append(("Name", original_url))
                    if original_discord_url and original_url == original_discord_url:
                        conflict_details.append(("Discord URL", original_url))
                    if tiktok_original_link and tiktok_link == tiktok_original_link:
                        conflict_details.append(("TikTok URL", original_url))
                    if insta_original_link and insta_link == insta_original_link:
                        conflict_details.append(
                            ("Instagram URL", original_url))
        return conflict_details

    async def add_video_to_database(self, name, url, color, original_url, added_by, tiktok_author_link=None, tiktok_original_link=None, tiktok_sound_link=None, insta_original_link=None, date_added=None, hashtags=None):
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                INSERT INTO videos 
                (name, url, color, original_url, added_by, tiktok_author_link, tiktok_original_link, tiktok_sound_link, insta_original_link, date_added, hashtags) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            values = (name, url, color, original_url, added_by, tiktok_author_link,
                      tiktok_original_link, tiktok_sound_link, insta_original_link, date_added, hashtags)
            try:
                await db.execute(query, values)
                await db.commit()
                if color in self.bot.video_lists and original_url not in self.bot.video_lists[color]:
                    self.bot.video_lists[color].append(original_url)
                    fisher_yates_shuffle(self.bot.video_lists[color])
            except aiosqlite.IntegrityError as e:
                print(f"Error adding video to the database: {e}")
        self.save_data()
