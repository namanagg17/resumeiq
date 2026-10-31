"""Load prompt files from prompts/ and fill in their {{placeholders}}.

A prompt file has an optional "### SYSTEM" section and a "### USER" section.
Placeholders use double braces ({{resume}}) so JSON examples inside prompts
do not need escaping.
"""

from __future__ import annotations

from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str) -> tuple[str, str]:
    """Return (system, user) templates for prompts/<name>.txt."""
    text = (PROMPT_DIR / f"{name}.txt").read_text(encoding="utf-8")
    system, user = "", text
    if "### USER" in text:
        before, user = text.split("### USER", 1)
        system = before.replace("### SYSTEM", "", 1)
    return system.strip(), user.strip()


def render(template: str, **values: str) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template
