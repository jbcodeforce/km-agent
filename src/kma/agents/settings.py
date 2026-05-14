from kma.db import create_knowledge, get_postgres_db

agent_db = get_postgres_db()
kma_knowledge = create_knowledge("kma Knowledge", "kma_knowledge")
kma_learnings = create_knowledge("kma Learnings", "kma_learnings")
