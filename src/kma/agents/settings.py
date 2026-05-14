from kma.db import create_knowledge, get_postgres_db

agent_db = get_postgres_db()
pal_knowledge = create_knowledge("Pal Knowledge", "pal_knowledge")
pal_learnings = create_knowledge("Pal Learnings", "pal_learnings")
