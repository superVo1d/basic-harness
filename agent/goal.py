
import json
import logging
import re

from agent.inference import call_model
from agent.session import Session

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """You are a strict judge evaluating whether an autonomous agent has achieved a user's stated goal. Decide one of four verdicts.
DONE — the goal is fully satisfied AND the deliverable actually exists.
BLOCKED — the goal genuinely cannot be satisfied, or the next step needs user input.
WAIT — not done, but the next step is to wait for async work.
CONTINUE — not done, and there is a concrete next step now. Default when in doubt.
Reply ONLY with one JSON object: {"verdict":"done|blocked|continue|wait","reason":"<one sentence>"}"""

JUDGE_USER_PROMPT = """Goal:
{goal}

Agent's most recent response:
{response}

Is the goal satisfied — done, blocked, continue, or wait?"""

CONTINUATION = """[Continuing toward your standing goal]
Goal: {goal}

Continue working toward this goal. Take the next concrete step. If the goal is complete, state so explicitly and stop. If blocked and need user input, say so and stop."""


def _parse_verdict(text: str) -> dict | None:
    """Extract the judge's JSON object from a possibly fenced/verbose reply."""
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = re.sub(r"^json\s*", "", t, flags=re.IGNORECASE)
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(t[start:end + 1])
    except json.JSONDecodeError:
        return None


def judge(session: Session) -> dict:
    """Ask the judge model for a verdict; fail open (continue) on any error."""
    last = session.history[-1] if session.history else {}
    response_text = last.get("content", "") if isinstance(last, dict) else str(last)
    try:
        resp = call_model([
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": JUDGE_USER_PROMPT.format(
                goal=session.goal, response=response_text)},
        ], tools=[])
    except Exception as e:
        logger.error("judge call failed: %s", e)
        return {"verdict": "continue", "reason": f"judge failed: {e}"}

    data = _parse_verdict(resp.output_text)
    if not data or "verdict" not in data:
        logger.error("judge: unparsable reply: %r", resp.output_text)
        return {"verdict": "continue", "reason": "unparsable judge reply"}
    return {"verdict": data["verdict"], "reason": data.get("reason", "")}


def continuation_message(goal: str) -> dict:
    """Get message to continue conversation."""
    return {"role": "user", "content": CONTINUATION.format(goal=goal)}
