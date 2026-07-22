-- Row counts for km-agent Knowledge / Learnings / Wiki stores (skips missing tables).
SELECT t.table_name AS store,
       (
         xpath(
           '/row/c/text()',
           query_to_xml(
             format('SELECT count(*) AS c FROM %I.%I', t.table_schema, t.table_name),
             false,
             true,
             ''
           )
         )
       )[1]::text::bigint AS rows
FROM information_schema.tables AS t
WHERE t.table_schema = 'public'
  AND t.table_type = 'BASE TABLE'
  AND t.table_name IN (
    'kma_knowledge',
    'kma_knowledge_contents',
    'kma_learnings',
    'kma_learnings_contents',
    'kma_wiki',
    'kma_wiki_contents'
  )
ORDER BY t.table_name;
