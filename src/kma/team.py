from agno.agent import Agent
from agno.learn import LearnedKnowledgeConfig, LearningMachine, LearningMode
from agno.team import Team, TeamMode
from kma.agents.settings import agent_db, kma_knowledge, kma_learnings
from kma.agents.compiler import compiler
from kma.agents.navigator import navigator
from kma.agents.researcher import researcher
from kma.llm_factory import build_default_llm_model


members: list[Agent | Team] = [m for m in [navigator, researcher, compiler] if m is not None]

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
kma_team = Team(
    id="kma",
    name="KMA",
    mode=TeamMode.coordinate,
    model=build_default_llm_model(),
    members=members,
    db=agent_db,
    instructions=[],
    tools=[],
    learning=LearningMachine(
        knowledge=kma_knowledge,
        learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
    ),
    add_learnings_to_context=True,
    enable_agentic_memory=True,
    search_past_sessions=True,
    num_past_sessions_to_search=10,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)