import disnake
from disnake.ext import commands
from config import GUILD_IDS, ALLOWED_USER_ID, update_cooldown
from utils import bot

@bot.slash_command(
    name="updatecooldown",
    description="Update the cooldown.",
    guild_ids=GUILD_IDS,
    options=[
        disnake.Option("value", "The value to set the cooldown to.", type=disnake.OptionType.integer, required=True),
        disnake.Option("unit", "The unit of time for the cooldown.", type=disnake.OptionType.string, required=True, choices=[
            disnake.OptionChoice("Days", "days"),
            disnake.OptionChoice("Hours", "hours"),
            disnake.OptionChoice("Seconds", "seconds")
        ])
    ]
)
async def updatecooldown(ctx, value: int, unit: str):
    if ctx.author.id != ALLOWED_USER_ID:
        await ctx.send("You do not have permission to use this command.")
        return

    if value < 0:
        await ctx.send("Cooldown value must be positive.")
        return

    if unit == "days":
        value_seconds = value * 86400
    elif unit == "hours":
        value_seconds = value * 3600
    else:
        value_seconds = value

    update_cooldown(value_seconds)
    await ctx.send(f"Cooldown updated to {value} {unit}.")
