# ADR 0007: Posting presence stored as validity periods

- Status: accepted
- Date: 2026-10-14 (implemented 2026-10-19)
- Note: `posting_pages` was renamed to `posting_details` in migration 0002 (2026-10-21), because "pages" was easy to read as the posting list.

## Context

Every run reads the full posting lists of a source, daily or after a gap of a few days. Trends, posting lifetimes and reposts need to know on which days each posting was listed and with which list fields. A run can fail halfway, and a source can be skipped for days. Posting pages weigh up to about 1 MB of HTML, mostly interface code, while the posting data itself is a few kilobytes of JSON.

## Decision

- **`postings`:** one row per posting address on one source, unique by `(source, source_key)`.
- **`posting_periods`:** one row per continuous period in which a posting was listed with the same list fields: first and last seen, the run that opened it and the run that closed it, with a reason (`gone` or `changed`). A partial unique index allows at most one open period per posting. A daily snapshot is a view computed from the periods, not a stored copy. This is the "valid from–to" history used in data warehouses (a type 2 slowly changing dimension).
- **Only a complete run closes a period as `gone`:** `runs.list_complete` is set when the whole list was read without errors, so one failed run cannot close thousands of postings.
- **`posting_details`:** only the JSON extracted from a posting's own page (requirements, description), never the HTML, stored as `jsonb` with lz4 compression. Each posting has zero, one or more versions: a new row is written only when the content hash changes. Pages are fetched for a subset of postings, so `postings` remains the only table with a row for every posting.
- **`runs`:** one row per fetch run, with counters, errors and the number of postings the source itself reports.

## Alternatives considered

- **A daily copy of every list:** the simplest to query, but it stores tens of thousands of nearly identical rows every day, and the table grows with time even when nothing changes.
- **A log of sightings, one row per posting per run:** keeps every observation, but grows as fast as daily copies, and every query has to rebuild the periods from it.
- **Posting details as a column of `postings`, overwritten on change:** one table fewer, but a report for a past month would change silently after a posting is edited, and the text that the LLM extracted values from would be lost. Keeping versions costs little because edits are rare, and the latest version is one query away.
- **An edited posting stored as a new posting:** would inflate posting counts, split one lifetime into two and count an edit as a new posting.
- **Storing the HTML of posting pages:** would allow parsing again later, but costs up to about 1 MB per page. The extracted JSON keeps the posting data, so a new field can still be filled from stored JSON without fetching again.

## Consequences

- A posting's lifetime is known only to the precision of the gap between runs, and a posting that appears and disappears between two runs is missed. Days without a complete run are visible in `runs`, so a gap in the data is not read as postings disappearing.
- Each run updates `last_seen_at` of every open period, tens of thousands of small updates that autovacuum handles.
- Source modules must drop volatile fields (view counters, "posted N days ago") before saving list data and pages; otherwise every run would open a new period or store a new page version.
- Old postings are never deleted, because trends and lifetimes need the full history.
