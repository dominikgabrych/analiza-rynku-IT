# ADR 0002: PostgreSQL with pgvector as the single data store

- Status: accepted
- Date: 2026-10-16 (recorded 2026-10-19)

## Context

The system stores postings, their history, extracted fields, logs of runs and model calls, and text chunks with embeddings for retrieval. Retrieval combines vector similarity with ordinary filters such as seniority, city and date. Everything runs on one machine with 16 GB of RAM, shared with a local LLM.

## Decision

- **One PostgreSQL 18 database with [pgvector](https://github.com/pgvector/pgvector)** holds both the relational data and the vectors.
- **It runs in Docker Compose** from an image pinned to an exact tag, with its port published on `127.0.0.1` only.

## Alternatives considered

- **A dedicated vector database (Qdrant, Chroma, Weaviate):** better scaling to very large collections, but a second store to keep in sync, back up and secure, and filters on posting fields would need copied metadata or joins in application code.
- **Elasticsearch or OpenSearch:** strong full-text search, but a memory-hungry JVM service and still a second store.

## Consequences

- One backup covers everything, and one set of roles controls access.
- One SQL query can filter by posting fields and rank by vector distance.
- HNSW indexes filter after the index scan, so a selective filter can return fewer rows than `LIMIT`; pgvector's iterative index scans are evaluated together with retrieval.
