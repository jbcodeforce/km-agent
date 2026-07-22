-- List base tables (excludes system catalogs).
SELECT table_schema AS schema, table_name AS "table"
FROM information_schema.tables
WHERE table_type = 'BASE TABLE'
  AND table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name;
