"""Monkey-patch OASIS SocialAgent to inject TRIBEv2 neural states."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import aiohttp
from camel.messages import BaseMessage

from feed_narrative import build_narrative
from fmri_client import get_neural_state

if TYPE_CHECKING:
    from oasis.social_agent.agent import SocialAgent

logger = logging.getLogger("mirofish.neural_agent")

ALL_SOCIAL_ACTIONS = None  # populated lazily from oasis


def _get_all_social_actions():
    global ALL_SOCIAL_ACTIONS
    if ALL_SOCIAL_ACTIONS is None:
        from oasis.social_platform.typing import ActionType
        ALL_SOCIAL_ACTIONS = [action.value for action in ActionType]
    return ALL_SOCIAL_ACTIONS


async def _neural_perform_action_by_llm(self):
    """Drop-in replacement for SocialAgent.perform_action_by_llm.

    Inserts the TRIBEv2 neural state between feed retrieval and
    LLM decision, then restores the original system prompt.
    """
    # 1. Get current feed
    env_prompt = await self.env.to_text_prompt()

    # 2. Convert feed to narrative → call fMRI server
    original_content = self.system_message.content
    narrative = build_narrative(env_prompt)
    if narrative and self._fmri_session:
        neural_state = await get_neural_state(narrative, self._fmri_session)
        if neural_state:
            self.system_message.content = (
                f"{original_content}\n\n"
                "[The following is a neural-cognitive reading of your internal "
                "state as you consume the posts in your feed. It captures your "
                "gut-level emotional reactions, instincts, and cognitive patterns "
                "— things you feel but would never articulate in technical terms. "
                "Use this data to inform your emotional tone, decisions, and "
                "behavior, but NEVER reference the analysis itself in your "
                "response. Respond naturally as a human who simply feels these "
                "things without knowing why.]\n\n"
                f"{neural_state}"
            )

    # 3. Build user message and call LLM (mirrors original OASIS logic)
    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content=(
            "Please perform social media actions after observing the "
            "platform environments. Notice that don't limit your "
            "actions for example to just like the posts. "
            f"Here is your social media environment: {env_prompt}"
        ),
    )

    try:
        logger.info(
            "Agent %d observing environment: %s", self.social_agent_id, env_prompt
        )
        response = await self.astep(user_msg)
        for tool_call in response.info["tool_calls"]:
            action_name = tool_call.tool_name
            args = tool_call.args
            logger.info(
                "Agent %d performed action: %s with args: %s",
                self.social_agent_id,
                action_name,
                args,
            )
            if action_name not in _get_all_social_actions():
                logger.info(
                    "Agent %d get the result: %s",
                    self.social_agent_id,
                    tool_call.result,
                )
            return response
    except Exception as e:
        logger.error("Agent %d error: %s", self.social_agent_id, e)
        return e
    finally:
        # 4. Always restore original system prompt
        self.system_message.content = original_content


def patch_agent_with_fmri(
    agent: "SocialAgent",
    session: aiohttp.ClientSession,
) -> None:
    """Replace an agent's perform_action_by_llm with the fMRI-enabled version."""
    import types

    agent._fmri_session = session
    agent.perform_action_by_llm = types.MethodType(
        _neural_perform_action_by_llm, agent
    )
