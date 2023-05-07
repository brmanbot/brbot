import disnake
from disnake.ext import commands
from utils import bot
from config import GUILD_IDS


@bot.slash_command(
    name="topreactions",
    description="Get top messages with most reactions in a channel. Max 25 results.",
    guild_ids=GUILD_IDS
)
async def topreactions(
    ctx: disnake.ApplicationCommandInteraction,
    results: int = commands.Param(10, desc="Number of results to display."),
    channel: disnake.TextChannel = commands.Param(None, desc="Target channel to check. Defaults to current channel.")
):
    await ctx.response.defer()

    if results > 25:
        embed = disnake.Embed(
            title=f"Error",
            description=f"You can only request up to 25 results.",
            color=0xF48BE3
        )
        await ctx.send(embed=embed)
        return

    if channel is None:
        channel = ctx.channel

    bot_permissions = channel.permissions_for(ctx.guild.me)
    if not bot_permissions.read_message_history or not bot_permissions.read_messages:
        embed = disnake.Embed(
            title="Error",
            description="I do not have the required permissions to read messages or message history in this channel.",
            color=0xF48BE3
        )
        await ctx.send(embed=embed)
        return

    messages = []
    async for message in channel.history(limit=None):
        messages.append(message)

    sorted_messages = sorted(messages, key=lambda msg: sum(reaction.count for reaction in msg.reactions), reverse=True)[:results]

    embed = disnake.Embed(title=f"Top {results} messages with most reactions in {channel.name}", description="", color=0xF48BE3)

    for i, message in enumerate(sorted_messages, start=1):
        reactions = ', '.join([f"{reaction.emoji} ({reaction.count})" for reaction in message.reactions])
        username = message.author.name
        message_url = f"https://discord.com/channels/{ctx.guild.id}/{channel.id}/{message.id}"
        embed.add_field(name=f"{i}. {username}", value=f"[{reactions}]({message_url})", inline=False)

    await ctx.send(embed=embed)
