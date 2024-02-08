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
                    tiktok_author_link TEXT,
                    tiktok_original_link TEXT,
                    tiktok_sound_link TEXT,
                    insta_original_link TEXT,
                    date_added TEXT,
                    is_hall_of_fame BOOLEAN DEFAULT 0
                )
            """)
            await db.commit()
    except aiosqlite.OperationalError as e:
        logging.error(f"Error initializing the database: {e}")


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
        query = "SELECT id, original_url FROM videos WHERE is_hall_of_fame = ?"
        values = (True,)
        try:
            cursor = await db.execute(query, values)
            return await cursor.fetchall()
        except aiosqlite.IntegrityError as e:
            logging.error(f"Error retrieving hall of fame videos: {e}")


async def synchronize_cache_with_database():
    cache_file_path = "video_data.json"
    db_path = "videos.db"
    conflicts = []

    async with aiosqlite.connect(db_path) as db:
        query = "SELECT original_url, COUNT(*) c FROM videos GROUP BY original_url HAVING c > 1"
        cursor = await db.execute(query)
        duplicates = await cursor.fetchall()

        if duplicates:
            for original_url, _ in duplicates:
                id_query = "SELECT id, name, color, added_by FROM videos WHERE original_url = ?"
                cursor = await db.execute(id_query, (original_url,))
                ids = [(row[0], row[1], row[2], row[3]) for row in await cursor.fetchall()]
                conflicts.append(
                    f"Duplicate URL found: {original_url}. Keeping ID: {ids[0][0]} (Name: {ids[0][1]}, Color: {ids[0][2]}, Added by: {ids[0][3]}), removing others.")
                for id_to_delete, _, _, _ in ids[1:]:
                    delete_query = "DELETE FROM videos WHERE id = ?"
                    await db.execute(delete_query, (id_to_delete,))

            await db.commit()

        db_videos = {}
        for color in ["green", "red", "yellow"]:
            async with db.execute("SELECT original_url, name FROM videos WHERE LOWER(color) = ?", (color.lower(),)) as cursor:
                db_videos[color] = {row[0]: row[1] for row in await cursor.fetchall()}

    if os.path.exists(cache_file_path):
        with open(cache_file_path, "r") as file:
            cache_data = json.load(file)
    else:
        cache_data = {"video_lists": {color: [] for color in [
            "green", "red", "yellow"]}, "last_reset": {}, "played_videos": {}, "hall_of_fame": []}

    for color, db_urls in db_videos.items():
        cached_urls = set(cache_data["video_lists"].get(color, []))
        db_url_set = set(db_urls.keys())
        added = db_url_set - cached_urls
        removed = cached_urls - db_url_set

        if added:
            added_details = [f"{url} (Name: {db_urls[url]})" for url in added]
            conflicts.append(f"Added to cache in '{color}': {added_details}")
        if removed:
            removed_details = [url for url in removed]
            conflicts.append(
                f"Removed from cache in '{color}': {removed_details}")

        cache_data["video_lists"][color] = list(db_url_set)

    with open(cache_file_path, "w") as file:
        json.dump(cache_data, file, indent=4)

    if conflicts:
        print("Conflicts detected and resolved during synchronization:")
        for conflict in conflicts:
            print(conflict)
    else:
        print("No conflicts found. Database and cache are synchronized.")
