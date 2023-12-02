import asyncio
import time
import disnake

from config import (
    ALLOWED_USER_ID,
    GREEN_ROLE_ID,
    GUILD_IDS,
    RED_ROLE_ID,
    YELLOW_ROLE_ID
)
from database import fisher_yates_shuffle
from utils import bot, load_setup_data, store_setup_data, load_role_timestamps, setup_data


async def send_message_and_add_reaction(channel, message):
    sent_message = await channel.send(message)
    await sent_message.add_reaction("✅")
    return sent_message.id

# @bot.slash_command(
#     name="setup_reaction_handler",
#     description="Sets up the reaction listener for a message with ✅, ❌, and 🤔 reactions.",
#     guild_ids=GUILD_IDS,
#     options=[
#         disnake.Option(
#             "channel",
#             "The channel where the message with reactions is located.",
#             type=disnake.OptionType.channel,
#             required=True
#         ),
#         disnake.Option(
#             "message_id",
#             "The ID of the message with reactions.",
#             type=disnake.OptionType.string,
#             required=True
#         ),
#         disnake.Option(
#             "target_channel",
#             "The channel where random videos should be sent.",
#             type=disnake.OptionType.channel,
#             required=True
#         )
#     ]
# )
# async def setup_reaction_handler(
#     ctx,
#     channel: disnake.TextChannel,
#     message_id: str,
#     target_channel: disnake.TextChannel
# ):
#     if ctx.author.id != ALLOWED_USER_ID:
#         await ctx.send("You are not authorised to use this command.", ephemeral=True)
#         return
    
#     await ctx.response.defer()

#     message_id = int(message_id)

#     try:
#         message_with_reactions = await channel.fetch_message(message_id)
#     except disnake.NotFound:
#         await ctx.send("Invalid message ID. Please try again.", ephemeral=True)
#         return
    
#     for reaction in ["✅", "❌", "🤔"]:
#         await message_with_reactions.add_reaction(reaction)

#     setup_data["message_id"] = message_with_reactions.id
#     setup_data["channel_id"] = channel.id
#     setup_data["target_channel_id"] = target_channel.id
#     store_setup_data(ctx.guild.id, message_with_reactions.id, channel.id, target_channel.id)
#     await ctx.send("Reaction handler setup complete.", ephemeral=True)

reaction_message_ids = {}

ALLOWED_EMOJIS = {"✅", "❌", "🤔"}

def setup(bot):
    @bot.event
    async def on_raw_reaction_add(payload):
        user = await bot.fetch_user(payload.user_id)
        if user.bot:
            return

        assert bot.video_manager is not None, "video_manager is not initialized"

        setup_data["message_id"], setup_data["channel_id"], setup_data["target_channel_id"] = load_setup_data(payload.guild_id)

        if payload.message_id != setup_data["message_id"] or payload.channel_id != setup_data["channel_id"]:
            if payload.message_id not in reaction_message_ids.get(payload.guild_id, []):
                return

        target_channel = bot.get_channel(setup_data["target_channel_id"])
        if target_channel is None:
            return

        guild = bot.get_guild(payload.guild_id)
        if guild is None:
            return

        all_guild_emojis = list(guild.emojis)
        fisher_yates_shuffle(all_guild_emojis)

        emoji = str(payload.emoji)
        random_emojis = all_guild_emojis[:4]

        yellow_role = disnake.utils.get(guild.roles, id=YELLOW_ROLE_ID)
        green_role = disnake.utils.get(guild.roles, id=GREEN_ROLE_ID)
        red_role = disnake.utils.get(guild.roles, id=RED_ROLE_ID)

        initial_yellow_role_users_count = len([member for member in guild.members if yellow_role in member.roles])

        if emoji not in ALLOWED_EMOJIS:
            return

        color = None
        if emoji == "✅":
            color = "green"
        elif emoji == "❌":
            color = "red"
        elif emoji == "🤔":
            color = "yellow"

        yellow_role_users = [member for member in guild.members if yellow_role in member.roles]

        played_videos = bot.video_manager.played_videos
        current_time = time.time()

        available_videos = await bot.video_manager.get_available_videos_with_cooldown([color], current_time, bot.cooldown)

        if not available_videos:
            await target_channel.send(f"No {color} videos found in the database that meet the cooldown requirement.")
            return

        chosen_video = available_videos[0]

        if not chosen_video:
            await target_channel.send("No videos found that meet the cooldown requirement.")
            return

        played_videos[chosen_video] = current_time
        bot.video_manager.save_data()

        await asyncio.sleep(0)

        emoji_to_color_and_message = {
            "✅": (f"{user.mention} is {green_role.mention} {random_emojis[1]}\n"),
            "❌": (f"{user.mention} is {red_role.mention} {random_emojis[2]}\n"),
            "🤔": (f"{user.mention} is {yellow_role.mention} {random_emojis[3]}\n")
        }

        user_message = emoji_to_color_and_message[emoji]

        if color == "green":
            if initial_yellow_role_users_count > 1:
                user_message += f"Does that change your mind {yellow_role.mention} {random_emojis[0]}❓\n\n{chosen_video}"
                message_in_target_channel_id = await send_message_and_add_reaction(target_channel, user_message)
                reaction_message_ids.setdefault(payload.guild_id, []).append(message_in_target_channel_id)
            else:
                user_message += f"\n{chosen_video}"
                await target_channel.send(user_message)