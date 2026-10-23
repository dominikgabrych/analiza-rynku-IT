# ADR 0007: Posting presence stored as validity periods

- Status: accepted
- Date: 2026-10-14 (implemented 2026-10-19; `posting_pages` renamed to `posting_details` on 2026-10-21)

## Context

Every run reads the full posting lists of a source. Trends and posting lifetimes need to know on which days each posting was listed, but a run can fail halfway and a source can be skipped for days. A posting page weighs up to about 1 MB of HTML, while its data is a few kilobytes of JSON.

## Decision

- **`posting_periods` stores continuous periods** in which a posting was listed with the same list fields, the "valid from–to" history of data warehouses (a type 2 slowly changing dimension). A daily snapshot is a view, not a stored copy.
- **Only a complete run closes a period**, so one failed run cannot make thousands of postings disappear.
- **`posting_details` keeps only the JSON extracted from a posting's page**, never the HTML, with a new version only when the content changes.
- **`postings` has one row per posting and `runs` one row per run**, and every period and version records the run that wrote it.

## Alternatives considered

- **A daily copy of every list:** simplest to query, but tens of thousands of nearly identical rows every day.
- **One row per posting per run:** grows as fast, and every query has to rebuild the periods.
- **Details overwritten on change:** past reports would change silently, and the text the LLM read would be lost.
- **Storing the HTML:** about 1 MB per page; the extracted JSON keeps the posting data.

## Consequences

- A posting's lifetime is known to the precision of the gap between runs, and a posting listed only between two runs is missed.
- Source modules must drop volatile fields, such as view counters, or every run would open a new period.
- Old postings are never deleted, because trends need the full history.
