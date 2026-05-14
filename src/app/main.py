
from os import getenv
from pathlib import Path

from agno.os import AgentOS
from kma.db import get_postgres_db
from kma.agents.compiler import compiler

from kma.agents.settings import kma_knowledge, kma_learnings
from kma.team import kma_team

agents: list = [a for a in [compiler] if a is not None]

agent_os = AgentOS(
    name="Pal",
    tracing=True,
    db=get_postgres_db(),
    teams=[kma_team],
    agents=agents,
    knowledge=[kma_knowledge, kma_learnings],
    config=str(Path(__file__).parent / "config.yaml"),
)

app = agent_os.get_app()


if __name__ == "__main__":
    agent_os.serve(
        app="app.main:app",
        reload=True,
    )
