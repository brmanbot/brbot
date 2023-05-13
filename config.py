import disnake
import json
from private_config import BOT_TOKEN, GUILD_IDS, ADMIN, ADMIN_ROLE

BOSSMANROLE_ID = ADMIN_ROLE
ALLOWED_USER_ID = ADMIN

INTENTS = disnake.Intents.default()
INTENTS.messages = True
INTENTS.reactions = True
INTENTS.typing = False
INTENTS.presences = False

BOT_TOKEN = BOT_TOKEN
GUILD_IDS = GUILD_IDS

def read_config_data():
    with open("config_data.json", "r") as file:
        data = json.load(file)
    return data

def get_cooldown():
    config_data = read_config_data()
    return config_data["cooldown"]

def update_cooldown(value):
    config_data = read_config_data()
    config_data["cooldown"] = value
    with open("config_data.json", "w") as file:
        json.dump(config_data, file)

config_data = read_config_data()
COOLDOWN = config_data["cooldown"]
