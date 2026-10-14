# analiza-rynku-IT

[![CI](https://github.com/dominikgabrych/analiza-rynku-IT/actions/workflows/ci.yml/badge.svg)](https://github.com/dominikgabrych/analiza-rynku-IT/actions/workflows/ci.yml)

IT job market analysis (*analiza rynku IT* is Polish for "IT market analysis"). The tool collects job postings, extracts seniority, skills and salary ranges with a local LLM, and uses SQL to show what employers expect at each level, from internship to senior, with AI roles analyzed against the IT market as a whole.

**Status:** early development.

## Principles

- **Every number has context.** Each statistic is reported with its sample size, time window and population. Small samples get an uncertainty interval or "not enough data".
- **Every extracted value has a quote.** The model quotes the posting for each value it extracts, and code verifies the quote. Values without a verified quote never reach the statistics.
- **SQL counts, the model reads.** The LLM only extracts data and describes results. Every metric is defined once, as an SQL view.
- **Local first.** Models run locally through Ollama, so processing thousands of postings costs nothing.

## Planned stack

Python (uv, ruff, pytest) · FastAPI · PostgreSQL with pgvector · Ollama · n8n · Grafana · Arize Phoenix · Docker Compose

## Development

Requires [uv](https://docs.astral.sh/uv/), which installs the Python version from `.python-version` and the locked dependencies.

```sh
uv sync              # create .venv with Python and the dev tools
uv run pytest        # run the tests
uv run ruff check    # lint
uv run ruff format   # format
```

Architecture decisions are recorded in [docs/adr](docs/adr/).

## License

[MIT](LICENSE)
