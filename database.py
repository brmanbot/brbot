import aiosqlite
import random
import time
from config import COOLDOWN

video_lists = {}
last_reset = {}


def fisher_yates_shuffle(arr):
    for i in range(len(arr) - 1, 0, -1):
        j = random.randint(0, i)
        arr[i], arr[j] = arr[j], arr[i]


async def initialize_database():
    try:
        async with aiosqlite.connect("videos.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    url TEXT,
                    color TEXT,
                    original_url TEXT
                )
            """)
            await db.commit()
    except Exception as e:
        print(f"Error initializing the database: {e}")


async def add_video_to_database(name, url, color, original_url):
    async with aiosqlite.connect("videos.db") as db:
        query = "INSERT INTO videos (name, url, color, original_url) VALUES (?, ?, ?, ?)"
        values = (name, url, color, original_url)
        await db.execute(query, values)
        await db.commit()