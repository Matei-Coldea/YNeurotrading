"""Convert OASIS env_prompt (feed text) into ~250-word narration for TRIBEv2."""

from __future__ import annotations

import json
import re


def build_narrative(env_prompt: str) -> str | None:
    """Parse OASIS env_prompt and convert to naturalistic narration.

    Args:
        env_prompt: Raw string from ``agent.env.to_text_prompt()``.
            Contains JSON-encoded posts inside square brackets.

    Returns:
        ~200-250 word factual narration suitable for TRIBEv2, or *None*
        if the feed is empty / unparseable.
    """
    posts = _extract_posts(env_prompt)
    if not posts:
        return None

    parts: list[str] = []
    ordinals = ["first", "second", "third", "fourth", "fifth"]

    for idx, post in enumerate(posts):
        content = post.get("content", "").strip()
        if not content:
            continue

        user_id = post.get("user_id", "unknown")
        likes = post.get("num_likes", 0)
        dislikes = post.get("num_dislikes", 0)
        shares = post.get("num_shares", 0)
        reports = post.get("num_reports", 0)

        # Position phrase
        if idx == 0:
            opener = "A post appears on the timeline"
        else:
            ord_label = ordinals[idx] if idx < len(ordinals) else f"next"
            opener = f"Below it, a {ord_label} post appears"

        opener += f" from user {user_id}"

        # Quote content
        sentence = f'{opener}. It reads: "{content}"'

        # Engagement — only mention non-zero counts
        engagement: list[str] = []
        if likes:
            engagement.append(f"{likes} like{'s' if likes != 1 else ''}")
        if shares:
            engagement.append(
                f"been shared {shares} time{'s' if shares != 1 else ''}"
            )
        if dislikes:
            engagement.append(
                f"{dislikes} dislike{'s' if dislikes != 1 else ''}"
            )
        if reports:
            engagement.append(
                f"{reports} report{'s' if reports != 1 else ''}"
            )

        if engagement:
            # Build a natural sentence from the parts
            eng_parts = []
            for e in engagement:
                if e.startswith("been"):
                    eng_parts.append(e)
                else:
                    eng_parts.append(f"has {e}" if not eng_parts else e)

            eng_str = " and ".join(eng_parts) if len(eng_parts) <= 2 else (
                ", ".join(eng_parts[:-1]) + f", and {eng_parts[-1]}"
            )
            # Normalise: ensure first part starts with "has" or "been"
            if eng_str.startswith("been"):
                sentence += f". The post has {eng_str}."
            elif eng_str.startswith("has"):
                sentence += f". The post {eng_str}."
            else:
                sentence += f". The post has {eng_str}."
        else:
            sentence += "."

        parts.append(sentence)

    if not parts:
        return None

    return " ".join(parts)


def _extract_posts(env_prompt: str) -> list[dict]:
    """Pull the JSON post list out of the OASIS env_prompt string."""
    # OASIS wraps posts in: "After refreshing, you see some posts [...]"
    # Find the JSON array that follows the posts marker, not any earlier arrays.
    marker = "you see some posts"
    marker_pos = env_prompt.find(marker)
    search_start = marker_pos + len(marker) if marker_pos != -1 else 0
    bracket_start = env_prompt.find("[", search_start)
    if bracket_start == -1:
        return []

    # Walk forward to find matching close bracket
    depth = 0
    for i in range(bracket_start, len(env_prompt)):
        if env_prompt[i] == "[":
            depth += 1
        elif env_prompt[i] == "]":
            depth -= 1
            if depth == 0:
                json_str = env_prompt[bracket_start : i + 1]
                break
    else:
        return []

    # Handle single-quoted JSON (OASIS sometimes outputs Python-style dicts)
    json_str = json_str.replace("'", '"')

    try:
        posts = json.loads(json_str)
        if isinstance(posts, list):
            return posts
    except json.JSONDecodeError:
        pass

    return []
