import aiosqlite
import random
import time
import logging

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