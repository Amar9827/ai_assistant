"""Personal memory system for JARVIS — loads user profile and corrections."""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MEMORY_DIR = Path(__file__).parent.parent.parent / "memory"
USER_PROFILE_PATH = MEMORY_DIR / "user_profile.json"
MAX_FACTS = 15
MAX_CORRECTIONS = 10


def _load_profile() -> dict:
    """Load user profile from JSON. Returns empty dict on any error."""
    try:
        if USER_PROFILE_PATH.exists():
            return json.loads(USER_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"[MEMORY] Failed to load profile: {e}")
    return {}


def _save_profile(profile: dict) -> None:
    """Save user profile to JSON."""
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        USER_PROFILE_PATH.write_text(
            json.dumps(profile, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning(f"[MEMORY] Failed to save profile: {e}")


def get_memory_context() -> str:
    """Build a concise context block from the user profile for the system prompt.

    Returns an empty string if no profile exists, so zero tokens are added.
    """
    profile = _load_profile()
    if not profile:
        return ""

    lines = ["PERSONAL CONTEXT (about your operator):"]

    name = profile.get("name")
    if name:
        lines.append(f"- Name: {name}")

    location = profile.get("location")
    if location:
        lines.append(f"- Location: {location}")

    tz = profile.get("timezone")
    if tz:
        lines.append(f"- Timezone: {tz}")

    prefs = profile.get("preferences", {})
    if prefs.get("address_as"):
        lines.append(f"- Address as: {prefs['address_as']}")
    if prefs.get("response_style"):
        lines.append(f"- Response style: {prefs['response_style']}")

    prof = profile.get("profession", {})
    if prof:
        parts = []
        if prof.get("title"):
            parts.append(prof["title"])
        if prof.get("experience_years"):
            parts.append(f"{prof['experience_years']}y experience")
        if prof.get("domain"):
            parts.append(prof["domain"])
        if parts:
            lines.append(f"- Profession: {', '.join(parts)}")
        if prof.get("expertise"):
            lines.append(f"- Expertise: {'; '.join(prof['expertise'])}")

    projects = profile.get("active_projects", [])
    if projects:
        lines.append(f"- Active projects: {'; '.join(projects)}")

    interests = profile.get("interests", [])
    if interests:
        lines.append(f"- Interests: {', '.join(interests)}")

    constraints = profile.get("constraints", [])
    if constraints:
        lines.append(f"- Constraints: {'; '.join(constraints)}")

    comm = profile.get("communication_notes", [])
    if comm:
        lines.append(f"- Communication: {'; '.join(comm)}")

    corrections = profile.get("corrections", [])[-MAX_CORRECTIONS:]
    if corrections:
        for c in corrections:
            wrong = c.get("wrong", "")
            correct = c.get("correct", "")
            query = c.get("query", "")
            if correct:
                entry = f"{query}: {correct}"
                if wrong:
                    entry += f" (NOT {wrong})"
                lines.append(f"- Past correction: {entry}")

    return "\n".join(lines)


def add_fact(fact: str) -> bool:
    """Add a user fact (e.g., 'prefers tea over coffee'). Returns True on success."""
    profile = _load_profile()
    facts = profile.setdefault("facts", [])
    if len(facts) >= MAX_FACTS:
        facts.pop(0)  # LRU eviction
    facts.append(fact.strip())
    _save_profile(profile)
    logger.info(f"[MEMORY] Added fact: {fact}")
    return True


def add_correction(query: str, wrong: str, correct: str) -> bool:
    """Record a user correction so JARVIS never repeats the mistake."""
    profile = _load_profile()
    corrections = profile.setdefault("corrections", [])
    if len(corrections) >= MAX_CORRECTIONS:
        corrections.pop(0)
    corrections.append({
        "query": query.strip(),
        "wrong": wrong.strip(),
        "correct": correct.strip(),
    })
    _save_profile(profile)
    logger.info(f"[MEMORY] Correction saved: {query} → {correct}")
    return True
