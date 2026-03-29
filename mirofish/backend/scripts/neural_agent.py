"""Monkey-patch OASIS SocialAgent to inject TRIBEv2 neural states."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

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
    print(f"[fMRI] Agent {self.social_agent_id}: start", flush=True)
    env_prompt = await self.env.to_text_prompt()

    # 2. Convert feed to narrative → call fMRI server
    original_content = self.system_message.content
    narrative = build_narrative(env_prompt)
    if narrative:
        try:
            print(f"[fMRI] Agent {self.social_agent_id}: calling server...", flush=True)
            neural_state = await asyncio.wait_for(
                get_neural_state(narrative),
                timeout=60,
            )
            print(f"[fMRI] Agent {self.social_agent_id}: got {'result' if neural_state else 'nothing'}", flush=True)
        except asyncio.TimeoutError:
            print(f"[fMRI] Agent {self.social_agent_id}: TIMEOUT", flush=True)
            neural_state = None
        except Exception as exc:
            print(f"[fMRI] Agent {self.social_agent_id}: ERROR {exc}", flush=True)
            neural_state = None

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
        print(f"[fMRI] Agent {self.social_agent_id}: calling LLM...", flush=True)
        response = await self.astep(user_msg)
        print(f"[fMRI] Agent {self.social_agent_id}: done", flush=True)
        for tool_call in response.info["tool_calls"]:
            action_name = tool_call.tool_name
            args = tool_call.args
            if action_name not in _get_all_social_actions():
                pass
            return response
    except Exception as e:
        print(f"[fMRI] Agent {self.social_agent_id}: LLM error: {e}", flush=True)
        return e
    finally:
        self.system_message.content = original_content


def patch_agent_with_fmri(agent: "SocialAgent") -> None:
    """Replace an agent's perform_action_by_llm with the fMRI-enabled version."""
    import types
    agent.perform_action_by_llm = types.MethodType(
        _neural_perform_action_by_llm, agent
    )
