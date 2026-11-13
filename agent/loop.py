"""V1 Agent Loop"""

from __future__ import annotations
import json
import logging
from typing import List, TypedDict

from agent.compression import maybe_compress
from agent.goal import continuation_message, judge
from agent.inference import call_model
from agent.registry import call_tool, tool_schemas
from agent.session import Session
from agent.workspace import set_current_session
import agent.tools  # noqa: F401  (импорт = регистрация)


logger = logging.getLogger(__name__)


MAX_TURN_CALLS = 50


class LoopState(TypedDict):
    """Conversation Loop state."""
    history: List[dict]
    iter: int = 0


def build_turn_context(session: Session) -> LoopState:
    """Create loop state, get session, get history."""
    return {
        "history": [
            {"role": "system", "content": session.system_prompt},
            *(session.summary_row() if session.summary else []),
            *session.messages()[session.summary_upto:]
        ],
        "iter": 0
    }


def _run_conversation(session: Session):
    """Handle conversation turn."""
    set_current_session(session.id)
    maybe_compress(session)
    ctx = build_turn_context(session)

    logger.info("— %s", ctx["history"][-1]["content"])

    final_response = ""

    while ctx["iter"] < MAX_TURN_CALLS:
        response = call_model(messages=ctx["history"], tools=tool_schemas())

        usage = getattr(response, "usage", None)
        if usage is not None:
            session.last_input_tokens = getattr(
                usage, "input_tokens", None) or getattr(usage, "prompt_tokens", 0)

        ctx["history"] += response.output
        ctx["iter"] += 1

        if response.output_text:
            logger.info("— %s", response.output_text)
            final_response = response.output_text

        tool_calls_count = 0

        for item in response.output:
            if item.type == "function_call":
                logger.info("→ %s, %s", item.name, item.arguments)
                tool_kwargs = json.loads(item.arguments) if item.arguments else {}
                tool_ctx = {"session_id": session.id}
                result = call_tool(item.name, tool_kwargs, tool_ctx)
                ctx["history"].append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result,
                })
                logger.info("← %s", result)
                tool_calls_count += 1

        if tool_calls_count == 0:
            break

    session.add({
        "role": "assistant",
        "content": final_response
    })
    return final_response


def run_agent(session: Session, budget: int = 20) -> str:
    """One turn; then, while a goal is active, keep going on the judge's verdict."""
    final_response = _run_conversation(session)
    if not session.goal:
        return final_response
    for _ in range(budget):
        verdict = judge(session)
        logger.info("judge: %s", verdict)
        if verdict["verdict"] != "continue":
            session.goal = None      # done / blocked / wait — stop pursuing the goal
            break
        session.add(continuation_message(session.goal))
        final_response = _run_conversation(session)
    return final_response
