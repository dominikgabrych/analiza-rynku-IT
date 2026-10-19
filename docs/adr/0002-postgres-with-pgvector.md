# ADR 0002: PostgreSQL with pgvector as the single data store

- Status: accepted
- Date: 2026-10-16 (recorded 2026-10-19)

## Context

The system stores job postings, the history of when each posting was listed, fields extracted by the LLM, logs of fetch runs and model calls, and, for retrieval-augmented generation (RAG), text chunks with their embeddings. Retrieval combines vector similarity with ordinary filters such as seniority, city, work mode and date, and every metric is defined once as an SQL view. Everything runs on one desktop machine with 16 GB of RAM, shared with a local LLM.

## Decision

- **One PostgreSQL database with the [pgvector](https://github.com/pgvector/pgvector) extension** stores both the relational data and the vectors.
- **PostgreSQL 18 runs in Docker Compose** from the `pgvector/pgvector` image pinned to an exact tag (`0.8.7-pg18-trixie`), so upgrades happen only in a reviewed change.
- **The port is published on `127.0.0.1` only**, so the database is not reachable from the local network. Data lives in the named volume `pgdata`, mounted at `/var/lib/postgresql` as the PostgreSQL 18 images expect.
- **A healthcheck with `pg_isready`** lets other services wait until the database accepts connections. The restart policy is `unless-stopped`.
- **Compose refuses to start without `POSTGRES_PASSWORD`** in `.env`, so the database never runs with an empty or default password.

## Alternatives considered

- **A dedicated vector database (Qdrant, Chroma, Weaviate) next to PostgreSQL:** more index tuning options and better scaling to very large collections. It would add a second store to keep in sync, back up and secure, and filters on posting metadata would need either a copy of that metadata in the vector store or joins across two systems in application code. It would also take memory that the LLM needs.
- **Elasticsearch or OpenSearch for hybrid search:** strong full-text search, but a JVM service with a large memory footprint, and still a second store.

## Consequences

- One `pg_dump` backs up everything, and one set of roles controls access (see [ADR 0003](0003-read-only-database-role.md)).
- A single SQL query can filter by metadata and rank by vector distance, and full-text search for hybrid retrieval lives in the same database. PostgreSQL has no built-in Polish text search configuration, so keyword search will use the `simple` configuration or `pg_trgm`, chosen by measurement.
- HNSW indexes apply filters after the index scan, so a selective filter can return fewer rows than `LIMIT`. pgvector's [iterative index scans](https://github.com/pgvector/pgvector#iterative-index-scans) address this and will be evaluated together with retrieval.
- The image is built with lz4, but the default TOAST compression is `pglz`, so large `jsonb` columns set `COMPRESSION lz4` explicitly in migrations.
- The expected scale (tens of thousands of postings, at most a few hundred thousand chunks) is comfortably within what pgvector handles on one machine.
