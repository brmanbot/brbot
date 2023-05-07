import disnake
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

COOLDOWN = 216000
