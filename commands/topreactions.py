import disnake
from disnake.ext import commands
from utils import bot
from config import GUILD_IDS
from datetime import datetime, timedelta
import pytz

@bot.slash_command(
    name="topreactions",
    description="Get top messages with most reactions in a channel.",
    guild_ids=GUILD_IDS,
    options=[
        disnake.Option("period", "Period for top reactions.", type=disnake.OptionType.string, required=False, choices=[
            disnake.OptionChoice("30 Days", "30d"),
            disnake.OptionChoice("3 Months", "3m"),
            disnake.OptionChoice("6 Months", "6m"),
            disnake.OptionChoice("1 Year", "1y"),
            disnake.OptionChoice("1.5 Years", "1.5y"),
            disnake.OptionChoice("2 Years", "2y"),
            disnake.OptionChoice("2.5 Years", "2.5y"),
            disnake.OptionChoice("3 Years", "3y"),
            disnake.OptionChoice("All Time", "all")
        ]),
        disnake.Option("channel", "Channel to check. Defaults to current channel.", type=disnake.OptionType.channel, required=False)
    ]
)
async def topreactions(ctx, period='all', channel=None):
    await ctx.response.defer()
    
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

    now = datetime.now(pytz.utc)

    periods = {
    '30d': 30,
    '3m': 90,
    '6m': 180,
    '1y': 365,
    '1.5y': int(365 * 1.5),
    '2y': 365 * 2,
    '2.5y': int(365 * 2.5),
    '3y': 365 * 3,
    'all': None
    }

    period_names = {
    '30d': '30 Days',
    '3m': '3 Months',
    '6m': '6 Months',
    '1y': '1 Year',
    '1.5y': '1.5 Years',
    '2y': '2 Years',
    '2.5y': '2.5 Years',
    '3y': '3 Years',
    'all': 'All Time'
    }

    days = periods.get(period)

    if days is not None:
        start_date = now - timedelta(days=days)
    else:
        start_date = None

    messages = []
    async for message in channel.history(limit=None):
        if message.reactions:
            messages.append(message)

    if start_date is not None:
        sorted_messages = sorted([message for message in messages if message.created_at.replace(tzinfo=pytz.UTC) >= start_date], 
                                 key=lambda msg: sum(reaction.count for reaction in msg.reactions), 
                                 reverse=True)[:25]
    else:
        sorted_messages = sorted([message for message in messages],
                                 key=lambda msg: sum(reaction.count for reaction in msg.reactions), 
                                 reverse=True)[:25]
                                 
    period_name = period_names.get(period)

    embed = disnake.Embed(title=f"Top messages with most reactions in {channel.name} for {period_name}", description="", color=0xF48BE3)

    for i, message in enumerate(sorted_messages, start=1):
        reactions = ', '.join([f"{reaction.emoji} ({reaction.count})" for reaction in message.reactions])
        username = message.author.name
        message_url = f"https://discord.com/channels/{ctx.guild.id}/{channel.id}/{message.id}"
        embed.add_field(name=f"{i}. {username}", value=f"[{reactions}]({message_url})", inline=False)

    await ctx.send(embed=embed)
