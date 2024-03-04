import aiosqlite
import disnake
from disnake import ApplicationCommandInteraction, OptionChoice
from utils import bot, autocomp_video_names, fetch_videos_by_name_or_hashtag
from config import GUILD_IDS
from rapidfuzz import process, fuzz


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
        user_input = user_input.lower().strip()
        all_matches = []

        exact_name_match_score = 10000
        exact_hashtag_match_score = 7500

        for video_name, video_info in inter.bot.video_manager.videos_info.items():
            if video_info is None:
                continue

            name_lower = video_name.lower()
            hashtags = (video_info.get("hashtags") or "").lower().split(',')
            hashtags_clean = [tag.strip() for tag in hashtags if tag.strip()]

            if user_input == name_lower:
                match_score = exact_name_match_score
            elif user_input in hashtags_clean:
                match_score = exact_hashtag_match_score
            else:
                name_score = process.extractOne(
                    user_input, [name_lower], scorer=fuzz.WRatio)[1]
                hashtag_scores = [process.extractOne(user_input, [tag], scorer=fuzz.WRatio)[
                    1] for tag in hashtags_clean]
                max_hashtag_score = max(hashtag_scores, default=0)
                match_score = max(name_score, max_hashtag_score * 0.9)

            if match_score > 60:
                all_matches.append((video_name, video_info, match_score))

        sorted_matches = sorted(
            all_matches, key=lambda x: x[2], reverse=True)[:25]

        suggestions = []
        for video_name, video_info, _ in sorted_matches:
            is_hall_of_fame = video_info["is_hall_of_fame"]
            hof_emoji = "🏆" if is_hall_of_fame else ""
            added_by = video_info["added_by"].split('#')[0]
            hashtags_clean = [f'#{tag}' for tag in (video_info.get(
                "hashtags") or "").lower().split(',') if tag.strip()]
            formatted_hashtags = ', '.join(hashtags_clean)

            suggestion_text = f"{hof_emoji}{video_name}".strip()
            if added_by:
                suggestion_text += f" [{added_by}]"
            if formatted_hashtags:
                suggestion_text += f" [{formatted_hashtags}]"

            suggestion_text = suggestion_text[:100]

            suggestions.append(disnake.OptionChoice(
                name=suggestion_text, value=video_name))

        return suggestions
