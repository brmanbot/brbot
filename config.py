import disnake
import json
from private_config import (
    BOT_TOKEN, GUILD_IDS, ADMIN, ADMIN_ROLE, 
    GREEN, RED, YELLOW,
    MOD_LOG,
)

BOSSMANROLE_ID = ADMIN_ROLE
ALLOWED_USER_ID = ADMIN

INTENTS = disnake.Intents.default()
INTENTS.messages = True
INTENTS.reactions = True
INTENTS.typing = False
INTENTS.presences = True
INTENTS.members = True

GREEN_ROLE_ID = GREEN
RED_ROLE_ID = RED
YELLOW_ROLE_ID = YELLOW

MOD_LOG = MOD_LOG

def get_config_data():
    try:
        with open("config_data.json", "r") as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print("config_data.json file does not exist.")
        return {}

def get_cooldown():
    config_data = get_config_data()
    return config_data.get("cooldown", None)

def update_cooldown(value):
    config_data = get_config_data()
    config_data["cooldown"] = value
    try:
        with open("config_data.json", "w") as file:
            json.dump(config_data, file)
    except Exception as e:
        print(f"An error occurred while updating cooldown: {e}")