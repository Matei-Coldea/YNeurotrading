"""
Synthetic Entity Generator

Generates diverse "regular people" EntityNode objects using a single LLM call
to create topic-aware persona sketches. These synthetic entities are injected
into the entity list and flow through the same profile/config generation
pipeline as graph-extracted entities.
"""

import uuid
import logging
from typing import List, Optional

from .entity_reader import EntityNode
from ..utils.llm_client import LLMClient

logger = logging.getLogger('mirofish.synthetic_entity_generator')


def generate_synthetic_entities(
    count: int,
    simulation_requirement: str,
    document_text: str,
    existing_entity_names: List[str],
) -> List[EntityNode]:
    """
    Generate N synthetic regular-person entities tailored to the simulation topic.

    Uses one LLM call to generate diverse persona sketches, then wraps each
    as an EntityNode that flows through the standard profile generation pipeline.

    Args:
        count: Number of synthetic entities to generate
        simulation_requirement: The simulation prompt/requirement
        document_text: The seed document text (truncated for context)
        existing_entity_names: Names of existing graph entities (to avoid overlap)

    Returns:
        List of EntityNode objects with labels=["Entity", "Person"]
    """
    sketches = _generate_persona_sketches(
        count=count,
        simulation_requirement=simulation_requirement,
        document_text=document_text[:2000],
        existing_entity_names=existing_entity_names,
    )

    entities = []
    for sketch in sketches:
        entity = EntityNode(
            uuid=f"synth-{uuid.uuid4()}",
            name=sketch.get("name", f"Person_{uuid.uuid4().hex[:6]}"),
            labels=["Entity", "Person"],
            summary=sketch.get("summary", ""),
            attributes={
                "synthetic": True,
                "profession": sketch.get("profession", ""),
            },
            related_edges=[],
            related_nodes=[],
        )
        entities.append(entity)

    logger.info(f"Generated {len(entities)} synthetic entities")
    return entities


def _generate_persona_sketches(
    count: int,
    simulation_requirement: str,
    document_text: str,
    existing_entity_names: List[str],
) -> List[dict]:
    """
    Single LLM call to generate N diverse persona sketches for the simulation topic.
    """
    existing_names_str = ", ".join(existing_entity_names[:20]) if existing_entity_names else "none"

    system_prompt = """You are a social simulation designer. Your job is to create diverse, realistic persona sketches for regular everyday people who would react to a news event on social media.

Each persona must be a distinct individual — vary across ALL of these dimensions:
- Age: range from 18 to 75
- Gender: mix of male, female, non-binary
- Ethnicity/background: diverse mix reflecting the US population
- Profession: blue-collar, white-collar, students, retired, self-employed, unemployed, etc.
- Political leaning: conservative, liberal, moderate, apolitical, libertarian, etc.
- Tech-savviness: from barely-uses-social-media to extremely-online
- Location: urban, suburban, rural, different US regions
- Relevance to the topic: some directly affected, some tangentially interested, some just casual observers

Output a JSON array of persona objects. Each object has:
- "name": A realistic full name (first + last)
- "profession": Their job or role
- "summary": 1-2 sentences describing who they are and their likely perspective on this topic. Be specific and vivid — not generic.

Do NOT create personas that overlap with these existing entities: """ + existing_names_str

    user_prompt = f"""Generate {count} diverse regular-person personas who would react to this scenario on social media:

**Scenario:** {simulation_requirement}

**Background context:**
{document_text}

Return a JSON array of {count} persona objects."""

    try:
        client = LLMClient()
        result = client.chat_json(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.9,
            max_tokens=4096,
        )

        # Handle both direct array and wrapped responses
        if isinstance(result, list):
            sketches = result
        elif isinstance(result, dict):
            # Try common wrapper keys
            for key in ["personas", "people", "results", "data"]:
                if key in result and isinstance(result[key], list):
                    sketches = result[key]
                    break
            else:
                # Take the first list value found
                for v in result.values():
                    if isinstance(v, list):
                        sketches = v
                        break
                else:
                    logger.error(f"Unexpected LLM response format: {list(result.keys())}")
                    return _fallback_sketches(count, simulation_requirement)
        else:
            logger.error(f"Unexpected LLM response type: {type(result)}")
            return _fallback_sketches(count, simulation_requirement)

        logger.info(f"LLM generated {len(sketches)} persona sketches")
        return sketches[:count]

    except Exception as e:
        logger.error(f"Persona sketch generation failed: {e}")
        return _fallback_sketches(count, simulation_requirement)


def _fallback_sketches(count: int, simulation_requirement: str) -> List[dict]:
    """
    Fallback if LLM call fails — generates basic diverse sketches without LLM.
    """
    topic_hint = simulation_requirement[:80]
    fallback_pool = [
        ("Alex Chen", "software engineer", "A 28-year-old software engineer who follows tech policy closely"),
        ("Maria Rodriguez", "nurse", "A 42-year-old nurse and mother of two who gets news from social media"),
        ("James Williams", "retired teacher", "A 67-year-old retired high school teacher, politically moderate"),
        ("Priya Patel", "college student", "A 21-year-old college student studying political science"),
        ("Marcus Johnson", "truck driver", "A 45-year-old truck driver, skeptical of government overreach"),
        ("Sarah Kim", "small business owner", "A 35-year-old small business owner running an online shop"),
        ("David Brown", "construction worker", "A 52-year-old construction worker, doesn't follow politics much"),
        ("Emily Zhang", "graduate student", "A 24-year-old computer science grad student, very online"),
        ("Robert Taylor", "accountant", "A 58-year-old accountant, fiscally conservative, socially moderate"),
        ("Jessica Martinez", "stay-at-home parent", "A 33-year-old stay-at-home mom, active in local community groups"),
        ("Tyler Washington", "high school student", "An 18-year-old high school senior, first-time voter"),
        ("Linda O'Brien", "real estate agent", "A 48-year-old real estate agent in a suburban area"),
        ("Ahmed Hassan", "uber driver", "A 38-year-old rideshare driver and recent immigrant"),
        ("Brittany Lewis", "barista", "A 26-year-old barista with a side hustle selling art online"),
        ("Frank Miller", "factory worker", "A 55-year-old factory worker in the Midwest, union member"),
        ("Sophia Nguyen", "freelance designer", "A 30-year-old freelance graphic designer, progressive"),
        ("Chris Anderson", "plumber", "A 41-year-old self-employed plumber, libertarian-leaning"),
        ("Diana Washington", "librarian", "A 60-year-old public librarian concerned about information access"),
        ("Kevin Park", "data analyst", "A 27-year-old data analyst, tech-savvy and privacy-conscious"),
        ("Michelle Thompson", "pediatrician", "A 44-year-old pediatrician, moderate Democrat"),
        ("Brandon Garcia", "electrician", "A 36-year-old electrician, doesn't trust mainstream media"),
        ("Rachel Green", "marketing manager", "A 31-year-old marketing manager, socially active online"),
        ("William Davis", "farmer", "A 62-year-old farmer in rural Iowa, lifelong Republican"),
        ("Jasmine Lee", "content creator", "A 23-year-old TikTok content creator with 50k followers"),
        ("Patrick Murphy", "firefighter", "A 39-year-old firefighter, politically independent"),
    ]

    sketches = []
    for i in range(count):
        name, profession, summary = fallback_pool[i % len(fallback_pool)]
        sketches.append({
            "name": name,
            "profession": profession,
            "summary": f"{summary}, following news about {topic_hint}.",
        })

    logger.warning(f"Using fallback sketches ({count} entities)")
    return sketches
