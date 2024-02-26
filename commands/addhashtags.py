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


class AddHashtags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="addhashtags",
        description="Add hashtags to an existing video in the database.",
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
    async def addhashtags(self, inter: ApplicationCommandInteraction, name: str, **hashtags):
        if not await has_role_check(inter):
            await inter.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        normalized_hashtags = normalize_hashtags(*hashtags.values())

        async with aiosqlite.connect("videos.db") as db:
            async with db.execute("SELECT hashtags FROM videos WHERE name = ?", (name,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                await inter.response.send_message(f"No video found with the name `{name}`.", ephemeral=True)
                return

            existing_hashtags = row[0] if row[0] else ''
            updated_hashtags = normalize_hashtags(
                existing_hashtags, normalized_hashtags)
            await db.execute("UPDATE videos SET hashtags = ? WHERE name = ?", (updated_hashtags, name))
            await db.commit()

            await inter.response.send_message(f"Updated hashtags for `{name}`: `{updated_hashtags}`.", ephemeral=True)

    @addhashtags.autocomplete("name")
    async def name_autocomplete(self, inter: ApplicationCommandInteraction, user_input: str):
        return await autocomp_video_names(inter, user_input)

    async def autocomplete_hashtag(inter: ApplicationCommandInteraction, user_input: str):
        all_hashtags = await fetch_all_hashtags()
        filtered_hashtags = [
            ht for ht in all_hashtags if user_input.lower() in ht.lower()]
        return [OptionChoice(name=ht, value=ht) for ht in filtered_hashtags][:25]

    hashtag_option_names = [f"hashtag_{i}" for i in range(1, 11)]
    for option_name in hashtag_option_names:
        addhashtags.autocomplete(option_name)(autocomplete_hashtag)


def setup(bot):
    bot.add_cog(AddHashtags(bot))
