import asyncio
import json
import os
import aiosqlite
from database import fisher_yates_shuffle
from config import MOD_LOG

COLORS = ["green", "red", "yellow"]

class VideoManager:
    def __init__(self, bot):
        self.bot = bot
        self.video_lists = {}
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
            
            self.hall_of_fame = [result[2] for result in results]

    async def load_data(self):
        try:
            if not os.path.isfile("video_data.json"):
                await self.load_hall_of_fame()
                self.save_data()
            else:
                with open("video_data.json", "r") as f:
                    data = json.load(f)
                    self.video_lists = data.get("video_lists", {})
                    self.last_reset = data.get("last_reset", {})
                    self.played_videos = data.get("played_videos", {})
                    self.hall_of_fame = data.get("hall_of_fame", [])  
        except Exception as e:
            print(f"Error loading data from file: {e}")
            raise e
    
    @classmethod
    async def create(cls, bot):
        video_manager = cls(bot)
        await video_manager.load_data()
        return video_manager
    
    def save_data(self):
        try:
            with open("video_data.json", "w") as f:
                data = {
                    "video_lists": self.video_lists,
                    "last_reset": self.last_reset,
                    "played_videos": self.played_videos,
                    "hall_of_fame": self.hall_of_fame
                }
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving data to file: {e}")
            raise e

    async def remove_video(self, identifier, identifier_type, MOD_LOG, deleted_by):
        removed_url = None
        removed_name = None
        added_by = None

        async with aiosqlite.connect("videos.db") as db:
            for color in COLORS:
                query = f"SELECT * FROM videos WHERE {identifier_type} = ? AND color = ?"
                values = (identifier, color)
                async with db.execute(query, values) as cursor:
                    result = await cursor.fetchone()
                    if result is not None:
                        removed_name = result[1]
                        removed_url = result[2]
                        vidcolor= result[3]
                        removed_og_url = result[4]
                        added_by = result[6]
                        await db.execute(f"DELETE FROM videos WHERE {identifier_type} = ? AND color = ?", (identifier, color))
                        await db.commit()
                        break

        if removed_url is not None and removed_name is not None:
            for color in COLORS:
                if color not in self.video_lists:
                    self.video_lists[color] = []
                if removed_url in self.video_lists[color]:
                    self.video_lists[color].remove(removed_url)

            if removed_url in self.played_videos:
                del self.played_videos[removed_url]

            if removed_url in self.hall_of_fame:
                self.hall_of_fame.remove(removed_url)

            username, discriminator = added_by.split("#")
            user = next((u for u in self.bot.users if u.name == username and u.discriminator == discriminator), None)

            if user and user.id != deleted_by.id:
                channel = self.bot.get_channel(MOD_LOG)
                if channel:
                    message = f"<@{user.id}> your video `{removed_name}` has been deleted by `{deleted_by.name}` from the `{vidcolor}` database <a:ALERT:916868273142906891>\n{removed_og_url}"
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
                        matched_videos.extend([video[1] for video in result])
        return matched_videos

    # async def get_available_videos(self, colors):
    #     current_time = time.time()
    #     available_videos = []

    #     async with aiosqlite.connect("videos.db") as db:
    #         for c in colors:
    #             if not self.video_lists.get(c) or (current_time - self.last_reset.get(c, 0) > 129600):
    #                 query = "SELECT url FROM videos WHERE color = ?"
    #                 values = (c,)
    #                 async with db.execute(query, values) as cursor:
    #                     results = await cursor.fetchall()

    #                 self.video_lists[c] = [url for url, in results]
    #                 self.last_reset[c] = current_time
    #                 fisher_yates_shuffle(self.video_lists[c])

    #             available_videos.extend(self.video_lists[c])

    #     return available_videos
    
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

    async def get_available_videos_with_cooldown(self, colors, current_time, cooldown):
        tasks = [self._get_videos_for_color(c, current_time, cooldown) for c in colors]
        results = await asyncio.gather(*tasks)

        available_videos = []
        for videos in results:
            available_videos.extend(videos)

        fisher_yates_shuffle(available_videos)
        return available_videos

    async def _get_videos_for_color(self, color, current_time, cooldown):
        if not self.video_lists.get(color) or (current_time - self.last_reset.get(color, 0) > 129600):
            query = "SELECT url FROM videos WHERE color = ?"
            values = (color,)
            async with aiosqlite.connect("videos.db") as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(query, values)
                results = await cursor.fetchall()

            self.video_lists[color] = [url for url, in results]
            self.last_reset[color] = current_time
            fisher_yates_shuffle(self.video_lists[color])

        return [video for video in self.video_lists[color] if current_time - self.played_videos.get(video, 0) > cooldown]
    
    async def update_hall_of_fame(self, identifier: str):
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT * FROM videos WHERE name = ? OR url = ?"
            values = (identifier, identifier)
            async with db.execute(query, values) as cursor:
                result = await cursor.fetchone()

        if result is not None:
            video_url = result[2]  
            if video_url not in self.hall_of_fame:
                self.hall_of_fame.append(video_url)
            self.save_data()
    
    async def fetch_video_info(self, url: str):
        async with aiosqlite.connect("videos.db") as db:
            query = "SELECT name, color, added_by FROM videos WHERE url = ? OR original_url = ?"
            values = (url, url)
            async with db.execute(query, values) as cursor:
                result = await cursor.fetchone()
        return result