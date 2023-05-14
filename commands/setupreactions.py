import time
import disnake
from disnake.ext import commands
import asyncio


from config import (
    GREEN_ROLE_ID,
    RED_ROLE_ID,
    YELLOW_ROLE_ID,
    GREEN_ROLE_DURATION,
    RED_ROLE_DURATION,
    YELLOW_ROLE_DURATION,
    ALLOWED_USER_ID,
    COOLDOWN,
    GUILD_IDS
)
from database import fisher_yates_shuffle
from utils import VideoManager, bot, load_setup_data, store_setup_data, setup_data, load_role_timestamps, store_role_timestamps

video_manager = None

@bot.slash_command(
    name="setup_reaction_handler",
    description="Sets up the reaction listener for a message with ✅, ❌, and 🤔 reactions.",
    guild_ids=GUILD_IDS,
    options=[
        disnake.Option(
            "channel",
            "The channel where the message with reactions is located.",
            type=disnake.OptionType.channel,
            required=True
        ),
        disnake.Option(
            "message_id",
            "The ID of the message with reactions.",
            type=disnake.OptionType.string,
            required=True
        ),
        disnake.Option(
            "target_channel",
            "The channel where random videos should be sent.",
            type=disnake.OptionType.channel,
            required=True
        )
    ]
)
async def setup_reaction_handler(
    ctx,
    channel: disnake.TextChannel,
    message_id: str,
    target_channel: disnake.TextChannel
):
    if ctx.author.id != ALLOWED_USER_ID:
        await ctx.send("You are not authorised to use this command.", ephemeral=True)
        return
    
    await ctx.response.defer()

    message_id = int(message_id)

    try:
        message_with_reactions = await channel.fetch_message(message_id)
    except disnake.NotFound:
        await ctx.send("Invalid message ID. Please try again.", ephemeral=True)
        return
    
    for reaction in ["✅", "❌", "🤔"]:
        await message_with_reactions.add_reaction(reaction)

    setup_data["message_id"] = message_with_reactions.id
    setup_data["channel_id"] = channel.id
    setup_data["target_channel_id"] = target_channel.id
    store_setup_data(ctx.guild.id, message_with_reactions.id, channel.id, target_channel.id)
    await ctx.send("Reaction handler setup complete.", ephemeral=True)

@bot.event
async def on_raw_reaction_add(payload):
    user = await bot.fetch_user(payload.user_id)
    if user.bot:
        return

    global video_manager

    setup_data["message_id"], setup_data["channel_id"], setup_data["target_channel_id"] = load_setup_data(payload.guild_id)

    if payload.message_id != setup_data["message_id"] or payload.channel_id != setup_data["channel_id"]:
        return

    target_channel = bot.get_channel(setup_data["target_channel_id"])
    if target_channel is None:
        return

    emoji = str(payload.emoji)

    guild = bot.get_guild(payload.guild_id)
    member = await guild.fetch_member(payload.user_id)

    role_id = None
    role_duration = None
    color = None
    if emoji == "✅":
        role_id = GREEN_ROLE_ID
        role_duration = GREEN_ROLE_DURATION
        color = "green"
    elif emoji == "❌":
        role_id = RED_ROLE_ID
        role_duration = RED_ROLE_DURATION
        color = "red"
    elif emoji == "🤔":
        role_id = YELLOW_ROLE_ID
        role_duration = YELLOW_ROLE_DURATION
        color = "yellow"
    else:
        return

    role = guild.get_role(role_id)
    await member.add_roles(role)

    role_timestamps = load_role_timestamps(guild.id)
    role_timestamps[str(role_id)] = time.time() + role_duration
    store_role_timestamps(guild.id, role_timestamps)

    async def remove_role_later(member, role, delay):
        await asyncio.sleep(delay)
        updated_member = guild.get_member(member.id)
        if updated_member:
            await updated_member.remove_roles(role)

    bot.loop.create_task(remove_role_later(member, role, role_duration))

    played_videos = video_manager.played_videos
    current_time = time.time()

    available_videos = await video_manager.get_available_videos([color])

    if not available_videos:
        await target_channel.send(f"No {color} videos found in the database.")
        return

    chosen_video = None
    while available_videos:
        fisher_yates_shuffle(available_videos)
        candidate_video = available_videos.pop()

        played_time = played_videos.get(candidate_video, 0)
        if current_time - played_time > COOLDOWN:
            chosen_video = candidate_video
            break

    if not chosen_video:
        await target_channel.send("No videos found that meet the cooldown requirement.")
        return

    played_videos[chosen_video] = current_time
    video_manager.save_data()

    await target_channel.send(chosen_video)