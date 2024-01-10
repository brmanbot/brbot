import aiosqlite
import random
import time
import logging
import json
import os

DATABASE_NAME = "videos.db"

video_lists = {}
last_reset = {}


def fisher_yates_shuffle(arr):
    for i in range(len(arr) - 1, 0, -1):
        j = random.randint(0, i)
        arr[i], arr[j] = arr[j], arr[i]


async def initialize_database():
    try:
        async with aiosqlite.connect(DATABASE_NAME) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    url TEXT,
                    color TEXT,
                    original_url TEXT,
                    added_by TEXT,
                    is_hall_of_fame BOOLEAN DEFAULT 0
                )
            """)
            await db.commit()
    except aiosqlite.OperationalError as e:
        logging.error(f"Error initializing the database: {e}")


async def add_video_to_database(name, url, color, original_url, added_by):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        query = "INSERT INTO videos (name, url, color, original_url, added_by) VALUES (?, ?, ?, ?, ?)"
        values = (name, url, color, original_url, added_by)
        try:
            await db.execute(query, values)
            await db.commit()
        except aiosqlite.IntegrityError as e:
            logging.error(f"Error adding video to the database: {e}")

async def add_video_to_hall_of_fame(id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        query = "UPDATE videos SET is_hall_of_fame = ? WHERE id = ?"
        values = (True, id)
        try:
            await db.execute(query, values)
            await db.commit()
        except aiosqlite.IntegrityError as e:
            logging.error(f"Error adding video to the hall of fame: {e}")

async def get_hall_of_fame_videos():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        query = "SELECT id, url FROM videos WHERE is_hall_of_fame = ?"
        values = (True,)
        try:
            cursor = await db.execute(query, values)
            return await cursor.fetchall()
        except aiosqlite.IntegrityError as e:
            logging.error(f"Error retrieving hall of fame videos: {e}")

async def synchronize_cache_with_database():
    cache_file_path = "video_data.json"
    db_path = "videos.db"
    
    async with aiosqlite.connect(db_path) as db:
        
        query = "SELECT url, COUNT(*) c FROM videos GROUP BY url HAVING c > 1"
        cursor = await db.execute(query)
        duplicates = await cursor.fetchall()

        for url, _ in duplicates:
            id_query = "SELECT id FROM videos WHERE url = ?"
            cursor = await db.execute(id_query, (url,))
            ids = [row[0] for row in await cursor.fetchall()]
            for id_to_delete in ids[1:]:
                delete_query = "DELETE FROM videos WHERE id = ?"
                await db.execute(delete_query, (id_to_delete,))

        await db.commit()

        db_videos = {}
        for color in ["green", "red", "yellow"]:
            async with db.execute("SELECT url FROM videos WHERE LOWER(color) = ?", (color.lower(),)) as cursor:
                db_videos[color] = [row[0] for row in await cursor.fetchall()]

    if os.path.exists(cache_file_path):
        with open(cache_file_path, "r") as file:
            cache_data = json.load(file)
            cache_data["video_lists"] = {color.lower(): urls for color, urls in cache_data["video_lists"].items()}
    else:
        cache_data = {"video_lists": {color: [] for color in ["green", "red", "yellow"]}, "last_reset": {}, "played_videos": {}}

    for color, urls in db_videos.items():
        cached_urls = set(cache_data["video_lists"].get(color, []))
        for url in urls:
            if url not in cached_urls:
                cache_data["video_lists"].setdefault(color, []).append(url)

        cache_data["video_lists"][color] = list(set(cache_data["video_lists"][color]))

    with open(cache_file_path, "w") as file:
        json.dump(cache_data, file, indent=4)

    print("Cache and database synchronized.")

