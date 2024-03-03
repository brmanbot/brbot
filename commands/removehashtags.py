import aiosqlite
import disnake
from disnake import ApplicationCommandInteraction, OptionChoice, OptionType
from disnake.ext import commands
import re
from config import GUILD_IDS
from utils import autocomp_video_names, fetch_all_hashtags, has_role_check


def normalize_hashtags(*hashtags):
    hashtag_list = []
    for hashtag in hashtags:
        if hashtag:
            hashtag_list.extend([tag.strip('#').lower()
                                for tag in re.split('[, ]+', hashtag.strip())])
    unique_hashtags = sorted(set(hashtag_list))
    return ','.join(unique_hashtags)


def remove_specific_hashtags(existing_hashtags_str, *hashtags_to_remove):
    existing_hashtags_set = set(existing_hashtags_str.split(','))
    hashtags_to_remove_set = set([tag.strip('#').lower()
                                 for tag in hashtags_to_remove])
    hashtags_actually_removed = existing_hashtags_set.intersection(
        hashtags_to_remove_set)
    updated_hashtags_set = existing_hashtags_set - hashtags_to_remove_set
    return ','.join(sorted(updated_hashtags_set)), hashtags_actually_removed


class RemoveHashtags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="removehashtags",
        description="Remove hashtags from an existing video in the database.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option(
                name="name",
                description="The name of the video to update.",
                type=OptionType.string,
                required=True,
                autocomplete=autocomp_video_names
            ),
            disnake.Option(
                name="hashtag_1",
                description="Hashtag 1.",
                type=OptionType.string,
                required=True
            ),
            disnake.Option(
                name=f"hashtag_2",
                description=f"Hashtag 2.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_3",
                description=f"Hashtag 3.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_4",
                description=f"Hashtag 4.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_5",
                description=f"Hashtag 5.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_6",
                description=f"Hashtag 6.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_7",
                description=f"Hashtag 7.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_8",
                description=f"Hashtag 8.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_9",
                description=f"Hashtag 9.",
                type=disnake.OptionType.string,
                required=False,
            ),
            disnake.Option(
                name=f"hashtag_10",
                description=f"Hashtag 10.",
                type=disnake.OptionType.string,
                required=False,
            )
        ]
    )
    async def removehashtags(self, inter: ApplicationCommandInteraction, name: str, **kwargs):
        if not await has_role_check(inter):
            await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        hashtags_to_remove = [
            hashtag for hashtag in kwargs.values() if hashtag]

        async with aiosqlite.connect("videos.db") as db:
            async with db.execute("SELECT hashtags FROM videos WHERE name = ?", (name,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                await inter.response.send_message(f"No video found with the name `{name}`.", ephemeral=True)
                return

            existing_hashtags = row[0] if row[0] else ''
            updated_hashtags, hashtags_actually_removed = remove_specific_hashtags(
                existing_hashtags, *hashtags_to_remove)
            await db.execute("UPDATE videos SET hashtags = ? WHERE name = ?", (updated_hashtags, name))
            await db.commit()

            await self.bot.video_manager.update_video_hashtags_in_cache(name, updated_hashtags)

            removed_hashtags_str = ', '.join(
                [f"#{ht}" for ht in hashtags_actually_removed])
            hashtag_or_hashtags = "hashtag" if len(
                hashtags_actually_removed) == 1 else "hashtags"
            new_hashtags_message = "No hashtags assigned anymore." if not updated_hashtags else f"New hashtags: `{updated_hashtags}`."
            message = f"Removed {hashtag_or_hashtags} `{removed_hashtags_str}` from `{name}`. {new_hashtags_message}"
            await inter.response.send_message(message, ephemeral=True)

    @removehashtags.autocomplete("name")
    async def name_autocomplete(self, inter: ApplicationCommandInteraction, user_input: str):
        return await autocomp_video_names(inter, user_input)

    async def autocomplete_hashtag(inter: ApplicationCommandInteraction, user_input: str):
        all_hashtags = await fetch_all_hashtags()
        filtered_hashtags = [
            ht for ht in all_hashtags if user_input.lower() in ht.lower()]
        return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]

    hashtag_option_names = [f"hashtag_{i}" for i in range(1, 11)]
    for option_name in hashtag_option_names:
        removehashtags.autocomplete(option_name)(autocomplete_hashtag)

    @removehashtags.autocomplete("hashtag_1")
    async def hashtag_autocomplete(self, inter: ApplicationCommandInteraction, user_input: str):
        video_name = None
        for option in inter.data.options:
            if option.name == "name":
                video_name = option.value
                break

        if video_name:
            hashtags = await self.fetch_hashtags_for_video(video_name)
            filtered_hashtags = [
                ht for ht in hashtags if user_input.lower() in ht.lower()]
            return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]
        else:
            return []

    @removehashtags.autocomplete("hashtag_2")
    async def hashtag_autocomplete(self, inter: ApplicationCommandInteraction, user_input: str):
        video_name = None
        for option in inter.data.options:
            if option.name == "name":
                video_name = option.value
                break

        if video_name:
            hashtags = await self.fetch_hashtags_for_video(video_name)
            filtered_hashtags = [
                ht for ht in hashtags if user_input.lower() in ht.lower()]
            return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]
        else:
            return []

    @removehashtags.autocomplete("hashtag_3")
    async def hashtag_autocomplete(self, inter: ApplicationCommandInteraction, user_input: str):
        video_name = None
        for option in inter.data.options:
            if option.name == "name":
                video_name = option.value
                break

        if video_name:
            hashtags = await self.fetch_hashtags_for_video(video_name)
            filtered_hashtags = [
                ht for ht in hashtags if user_input.lower() in ht.lower()]
            return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]
        else:
            return []

    @removehashtags.autocomplete("hashtag_4")
    async def hashtag_autocomplete(self, inter: ApplicationCommandInteraction, user_input: str):
        video_name = None
        for option in inter.data.options:
            if option.name == "name":
                video_name = option.value
                break

        if video_name:
            hashtags = await self.fetch_hashtags_for_video(video_name)
            filtered_hashtags = [
                ht for ht in hashtags if user_input.lower() in ht.lower()]
            return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]
        else:
            return []

    @removehashtags.autocomplete("hashtag_5")
    async def hashtag_autocomplete(self, inter: ApplicationCommandInteraction, user_input: str):
        video_name = None
        for option in inter.data.options:
            if option.name == "name":
                video_name = option.value
                break

        if video_name:
            hashtags = await self.fetch_hashtags_for_video(video_name)
            filtered_hashtags = [
                ht for ht in hashtags if user_input.lower() in ht.lower()]
            return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]
        else:
            return []

    @removehashtags.autocomplete("hashtag_6")
    async def hashtag_autocomplete(self, inter: ApplicationCommandInteraction, user_input: str):
        video_name = None
        for option in inter.data.options:
            if option.name == "name":
                video_name = option.value
                break

        if video_name:
            hashtags = await self.fetch_hashtags_for_video(video_name)
            filtered_hashtags = [
                ht for ht in hashtags if user_input.lower() in ht.lower()]
            return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]
        else:
            return []

    @removehashtags.autocomplete("hashtag_7")
    async def hashtag_autocomplete(self, inter: ApplicationCommandInteraction, user_input: str):
        video_name = None
        for option in inter.data.options:
            if option.name == "name":
                video_name = option.value
                break

        if video_name:
            hashtags = await self.fetch_hashtags_for_video(video_name)
            filtered_hashtags = [
                ht for ht in hashtags if user_input.lower() in ht.lower()]
            return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]
        else:
            return []

    @removehashtags.autocomplete("hashtag_8")
    async def hashtag_autocomplete(self, inter: ApplicationCommandInteraction, user_input: str):
        video_name = None
        for option in inter.data.options:
            if option.name == "name":
                video_name = option.value
                break

        if video_name:
            hashtags = await self.fetch_hashtags_for_video(video_name)
            filtered_hashtags = [
                ht for ht in hashtags if user_input.lower() in ht.lower()]
            return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]
        else:
            return []

    @removehashtags.autocomplete("hashtag_9")
    async def hashtag_autocomplete(self, inter: ApplicationCommandInteraction, user_input: str):
        video_name = None
        for option in inter.data.options:
            if option.name == "name":
                video_name = option.value
                break

        if video_name:
            hashtags = await self.fetch_hashtags_for_video(video_name)
            filtered_hashtags = [
                ht for ht in hashtags if user_input.lower() in ht.lower()]
            return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]
        else:
            return []

    @removehashtags.autocomplete("hashtag_10")
    async def hashtag_autocomplete(self, inter: ApplicationCommandInteraction, user_input: str):
        video_name = None
        for option in inter.data.options:
            if option.name == "name":
                video_name = option.value
                break

        if video_name:
            hashtags = await self.fetch_hashtags_for_video(video_name)
            filtered_hashtags = [
                ht for ht in hashtags if user_input.lower() in ht.lower()]
            return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]
        else:
            return []

    async def fetch_hashtags_for_video(self, video_name: str):
        async with aiosqlite.connect("videos.db") as db:
            async with db.execute("SELECT hashtags FROM videos WHERE name = ?", (video_name,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0].split(',') if row[0] else []
                return []


def setup(bot):
    bot.add_cog(RemoveHashtags(bot))
