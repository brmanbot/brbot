import disnake
import json
from private_config import BOT_TOKEN, GUILD_IDS, ADMIN, ADMIN_ROLE, GREEN, RED, YELLOW

BOSSMANROLE_ID = ADMIN_ROLE
ALLOWED_USER_ID = ADMIN

INTENTS = disnake.Intents.default()
INTENTS.messages = True
INTENTS.reactions = True
INTENTS.typing = False
INTENTS.presences = False
INTENTS.message_content = True

BOT_TOKEN = BOT_TOKEN
GUILD_IDS = GUILD_IDS

GREEN_ROLE_ID = GREEN
RED_ROLE_ID = RED
YELLOW_ROLE_ID = YELLOW

GREEN_ROLE_DURATION = 43200
RED_ROLE_DURATION = 43200
YELLOW_ROLE_DURATION = 36000

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
