from __future__ import annotations
from pathlib import Path

import pytest
from agno.run.base import RunStatus
from agno.run.agent import RunOutput
from kma.agents.linter import build_linter_agent
from pathlib import Path

IT_CONTEXT = Path(__file__).resolve().parent.parent / "data"
@pytest.mark.usefixtures("require_postgres")
def test_linter_agent_integration() -> None:

    agent = build_linter_agent(context_dir=IT_CONTEXT)
    assert agent is not None
    assert agent.model is not None
    assert agent.model.id == "Qwen3.6-27B-PARO"
    assert type(agent.model).__name__ == "OpenAILike"
    assert agent.instructions
    user_request = "Run the linter agent"
    try:
        final: RunOutput | None = None
        for chunk in agent.run(
            user_request,
            stream=True,
            stream_events=True,  # tool / model / reasoning-style events (see RunEvent)
            yield_run_output=True,  # also yield the final RunOutput in the stream
        ):
            if isinstance(chunk, RunOutput):
                final = chunk
        print(final)
        if final.status != RunStatus.completed:
            msg = (final.content or "").lower()
            if "memory" in msg or "not found" in msg or "requires more" in msg or "timeout" in msg:
                pytest.skip(f"Linter run infra issue: {final.content!r}")
        assert final.status == RunStatus.completed, f"linter run failed: {final.content!r}"

    except Exception as e:
        print(f"Error: {e}")
        raise e
   