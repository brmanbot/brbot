import aiosqlite
import disnake
from disnake import ApplicationCommandInteraction, OptionChoice
from utils import bot, autocomp_video_names, fetch_videos_by_name_or_hashtag
from config import GUILD_IDS


def setup(bot):
    @bot.slash_command(
        name="getvid",
        description="Retrieve the URL of a saved video by name. Use /vids to see a list of all available videos.",
        guild_ids=GUILD_IDS,
        options=[
            disnake.Option(
                "identifier",
                "The name or related hashtag of the video to retrieve.",
                type=disnake.OptionType.string,
                required=True,
                autocomplete=True
            )
        ]
    )
    async def getvid(ctx: ApplicationCommandInteraction, identifier: str):
        identifier = identifier.strip().lower()

        video_info = ctx.bot.video_manager.videos_info.get(identifier, None)

        if video_info:
            is_hall_of_fame = video_info["is_hall_of_fame"]
            hof_emoji = "🏆 " if is_hall_of_fame else ""
            message = f"{hof_emoji}[{identifier}]({video_info['original_url']})"
        else:
            message = "No matching videos found"

        await ctx.response.send_message(message)

    @getvid.autocomplete("identifier")
    async def getvid_autocomplete(inter: ApplicationCommandInteraction, user_input: str):
        user_input_terms = user_input.lower().strip().split()
        suggestions = []

        is_hof_search = user_input.lower().strip() == "hof"

        general_terms = [
            term for term in user_input_terms if not term.startswith("#")]
        hashtag_terms = [term[1:]
                         for term in user_input_terms if term.startswith("#")]

        for video_name, video_info in inter.bot.video_manager.videos_info.items():
            name_lower = video_name.lower()
            hashtags = (video_info.get("hashtags") or "").lower().split(',')
            hashtags_clean = [tag.strip()
                              for tag in hashtags if tag.strip()]

            is_hall_of_fame = video_info["is_hall_of_fame"]
            hof_emoji = "🏆" if is_hall_of_fame else ""
            added_by = video_info["added_by"].split('#')[0]
            formatted_hashtags = ', '.join(
                [f'#{tag}' for tag in hashtags_clean])

            suggestion_text = f"{hof_emoji}{video_name}".strip()
            if added_by:
                suggestion_text += f" [{added_by}]"
            if formatted_hashtags:
                suggestion_text += f" [{formatted_hashtags}]"

            matches_hof_criteria = is_hof_search and is_hall_of_fame
            general_match = any(term in name_lower or any(
                term in hashtag for hashtag in hashtags_clean) for term in general_terms)
            hashtag_match = all(any(hashtag_term in hashtag for hashtag in hashtags_clean)
                                for hashtag_term in hashtag_terms)

            if (matches_hof_criteria or general_match or not general_terms) and (hashtag_match or not hashtag_terms) and len(suggestions) < 25:
                suggestions.append(disnake.OptionChoice(
                    name=suggestion_text, value=video_name))

        return suggestions
