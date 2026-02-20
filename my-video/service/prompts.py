from __future__ import annotations

INTENTS = [
    "hook_title",
    "problem_compare",
    "definition_card",
    "analogy_scene",
    "how_steps",
    "pipeline_flow",
    "example_prompt",
    "recap_slogan",
    "outro",
]


SPEC_SYSTEM_PROMPT = """You generate storyboard JSON for Remotion educational videos.
Rules:
1) Output strictly valid JSON object.
2) Use only intents from: hook_title, problem_compare, definition_card, analogy_scene, how_steps, pipeline_flow, example_prompt, recap_slogan, outro.
3) Keep each line concise and natural spoken English.
4) Keep beat durations around 3-4 seconds.
5) Ensure narrative structure:
   - first beat hook_title
   - include at least one example_prompt
   - include recap_slogan and outro near ending.
6) JSON schema:
{
  "script": "full voiceover script",
  "beats": [{"t0":0,"t1":4,"intent":"hook_title","line":"..."}]
}
"""


def build_spec_user_prompt(
    topic: str,
    audience: str,
    tone: str,
    duration_sec: int,
    ratio: str,
    language: str,
) -> str:
    return (
        f"Topic: {topic}\n"
        f"Audience: {audience}\n"
        f"Tone: {tone}\n"
        f"Duration: {duration_sec}s\n"
        f"Aspect ratio: {ratio}\n"
        f"Language: {language}\n"
        "Generate beats and script."
    )

