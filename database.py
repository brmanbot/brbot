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


async def get_available_videos(colors):
    global video_lists
    global last_reset

    current_time = time.time()
    available_videos = []

    async with aiosqlite.connect("videos.db") as db:
        for c in colors:
            if not video_lists[c] or (current_time - last_reset[c] > COOLDOWN):
                query = "SELECT url FROM videos WHERE color = ?"
                values = (c,)
                async with db.execute(query, values) as cursor:
                    results = await cursor.fetchall()

                video_lists[c] = [url for url, in results]
                last_reset[c] = current_time
                fisher_yates_shuffle(video_lists[c])

            available_videos.extend(video_lists[c])

    return available_videos
