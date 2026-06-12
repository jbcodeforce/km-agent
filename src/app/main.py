
from os import getenv
from pathlib import Path

from agno.os import AgentOS
from kma.db import get_postgres_db
from kma.agents.compiler import get_compiler
from kma.agents.linter import get_linter
from kma.agents.navigator import get_navigator
from kma.agents.researcher import get_researcher

from kma.agents.settings import get_kma_knowledge, get_kma_learnings
from kma.agents.team import get_kma_team


def _build_agents() -> list:
    return [a for a in [get_compiler(), get_navigator(), get_linter(), get_researcher()] if a is not None]


agent_os = AgentOS(
    name="KM-Agent",
    tracing=True,
    db=get_postgres_db(),
    teams=[get_kma_team()],
    agents=_build_agents(),
    knowledge=[get_kma_knowledge(), get_kma_learnings()],
    config=str(Path(__file__).parent / "config.yaml"),
)

_api_app = agent_os.get_app()


def _serve_ui_enabled() -> bool:
    v = getenv("KMA_SERVE_UI", "").strip().lower()
    return v in ("1", "true", "yes")


def _static_dir() -> Path:
    override = getenv("KMA_STATIC_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _build_app():
    """AgentOS routes at / when UI is off; at /agent-os when UI is on (matches Vite dev proxy prefix)."""
    if not _serve_ui_enabled():
        return _api_app
    static = _static_dir()
    if not static.is_dir():
        return _api_app
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    root = FastAPI()
    root.mount("/agent-os", _api_app)
    root.mount("/", StaticFiles(directory=str(static), html=True), name="static")
    return root


app = _build_app()


if __name__ == "__main__":
    agent_os.serve(
        app="app.main:app",
        reload=True,
    )
