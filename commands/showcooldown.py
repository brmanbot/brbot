import disnake
from disnake.ext import commands
from config import GUILD_IDS, get_cooldown
from utils import bot

def format_cooldown(cooldown_value):
    days, remainder = divmod(cooldown_value, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    formatted_cooldown = []
    if days:
        formatted_cooldown.append(f"{days} days")
    if hours:
        formatted_cooldown.append(f"{hours} hours")
    if minutes:
        formatted_cooldown.append(f"{minutes} minutes")
    if seconds:
        formatted_cooldown.append(f"{seconds} seconds")

    return ", ".join(formatted_cooldown)

def setup(bot):
    @bot.slash_command(
        name="showcooldown",
        description="Display the current cooldown.",
        guild_ids=GUILD_IDS,
    )
    async def showcooldown(ctx):
        cooldown_value = get_cooldown()
        cooldown_formatted = format_cooldown(cooldown_value)
        await ctx.send(f"Current cooldown is: `{cooldown_formatted}`")
