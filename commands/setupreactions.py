import time
import disnake

from config import (
    ALLOWED_USER_ID,
    GUILD_IDS,
    YELLOW_ROLE_ID
)
from database import fisher_yates_shuffle
from utils import bot, load_setup_data, store_setup_data, load_role_timestamps, setup_data

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

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    all_guild_emojis = guild.emojis
    fisher_yates_shuffle(all_guild_emojis)

    emoji = str(payload.emoji)

    emoji_to_color_and_message = {
        "✅": ("green", f"{user.mention} is willing to game tonight\n"),
        "❌": ("red", f"{user.mention} is not gaming tonight\n"),
        "🤔": ("yellow", f"{user.mention} is thinking about gaming\n")
    }
    
    if emoji not in emoji_to_color_and_message:
        return

    color, user_message = emoji_to_color_and_message[emoji]

    yellow_role_users = []
    if color == "green":
        yellow_role = disnake.utils.get(guild.roles, id=YELLOW_ROLE_ID)
        if yellow_role:
            for member in guild.members:
                if yellow_role in member.roles:
                    yellow_role_users.append(member)

    if yellow_role_users:
        random_emoji = all_guild_emojis[0] if all_guild_emojis else '😅' 
        user_message += f"Does that change your mind {yellow_role.mention} {random_emoji}❓\n"
    
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
        if current_time - played_time > bot.cooldown:
            chosen_video = candidate_video
            break

    if not chosen_video:
        await target_channel.send("No videos found that meet the cooldown requirement.")
        return

    played_videos[chosen_video] = current_time
    video_manager.save_data()

    await target_channel.send(f"{user_message}\n{chosen_video}")