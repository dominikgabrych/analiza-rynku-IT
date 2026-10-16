#!/bin/bash
# Creates radar_reader, the read-only role for dashboards and other readers.
# The postgres image runs this only when the data volume is empty; later role
# changes belong in migrations.
set -euo pipefail

# :'reader_password' makes psql quote the value as an SQL string literal.
psql -v ON_ERROR_STOP=1 \
	--username "$POSTGRES_USER" \
	--dbname "$POSTGRES_DB" \
	-v reader_password="$RADAR_READER_PASSWORD" <<'EOSQL'
CREATE ROLE radar_reader LOGIN PASSWORD :'reader_password';

-- Grants are the real guard; these two defaults add a safety margin.
ALTER ROLE radar_reader SET default_transaction_read_only = on;
ALTER ROLE radar_reader SET statement_timeout = '30s';

GRANT CONNECT ON DATABASE :"DBNAME" TO radar_reader;
GRANT USAGE ON SCHEMA public TO radar_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO radar_reader;

-- Covers tables and views that postgres creates later.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
	GRANT SELECT ON TABLES TO radar_reader;
EOSQL
