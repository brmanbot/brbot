import aiosqlite
from utils import autocomp_video_names, bot, has_role_check
from config import GUILD_IDS
import disnake

def setup(bot):
    @bot.slash_command(
        name="addhof",
        description="Add a video to the Hall of Fame.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option(
                "identifier",
                "The identifier (name or URL) of the video.",
                type=disnake.OptionType.string,
                required=True,
                autocomplete=True
            )
        ]
    )
    async def hof(inter, identifier: str):
        if not await has_role_check(inter):
            await inter.response.send_message("You are not authorised to use this command.", ephemeral=True)
            return

        assert bot.video_manager is not None, "video_manager is not initialized"

        select_query = "SELECT * FROM videos WHERE name = ? OR url = ?"
        update_query = "UPDATE videos SET is_hall_of_fame = 1 WHERE name = ? OR url = ?"

        async with aiosqlite.connect("videos.db") as db:
            async with db.execute(select_query, (identifier, identifier)) as cursor:
                result = await cursor.fetchone()

            if result is None:
                await inter.response.send_message(f"The video `{identifier}` does not exist in the database.", ephemeral=True)
                return

            if result[7]:
                await inter.response.send_message(f"The video `{identifier}` is already in the Hall of Fame.", ephemeral=True)
                return

            try:
                await db.execute(update_query, (identifier, identifier))
                await db.commit()
                await bot.video_manager.update_hall_of_fame(result[1])
                await inter.response.send_message(f"Video `{result[1]}` has been added to the Hall of Fame.")
            except aiosqlite.Error as e:
                await inter.response.send_message(f"An error occurred while adding the video to the Hall of Fame: {e}", ephemeral=True)

    @hof.autocomplete("identifier")
    async def hof_autocomplete_name(inter: disnake.ApplicationCommandInteraction, user_input: str):
        return await autocomp_video_names(inter, user_input)
