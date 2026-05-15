"""Env toggles for Agno reasoning / stream progress (kma.config)."""

import os

from kma.config import (
    kma_agent_reasoning_enabled,
    kma_show_team_member_responses_enabled,
    kma_stream_events_enabled,
)


def test_trace_flags_default_false() -> None:
    prev = {
        "KMA_AGENT_REASONING": os.environ.get("KMA_AGENT_REASONING"),
        "KMA_STREAM_EVENTS": os.environ.get("KMA_STREAM_EVENTS"),
        "KMA_SHOW_TEAM_MEMBERS": os.environ.get("KMA_SHOW_TEAM_MEMBERS"),
    }
    try:
        for k in prev:
            os.environ.pop(k, None)
        assert kma_agent_reasoning_enabled() is False
        assert kma_stream_events_enabled() is False
        assert kma_show_team_member_responses_enabled() is False
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_trace_flags_truthy() -> None:
    prev = {
        "KMA_AGENT_REASONING": os.environ.get("KMA_AGENT_REASONING"),
        "KMA_STREAM_EVENTS": os.environ.get("KMA_STREAM_EVENTS"),
        "KMA_SHOW_TEAM_MEMBERS": os.environ.get("KMA_SHOW_TEAM_MEMBERS"),
    }
    os.environ["KMA_AGENT_REASONING"] = "1"
    os.environ["KMA_STREAM_EVENTS"] = "yes"
    os.environ["KMA_SHOW_TEAM_MEMBERS"] = "on"
    try:
        assert kma_agent_reasoning_enabled() is True
        assert kma_stream_events_enabled() is True
        assert kma_show_team_member_responses_enabled() is True
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
