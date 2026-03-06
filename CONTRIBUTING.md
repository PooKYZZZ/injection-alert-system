# Contributing

Thanks for taking the time to contribute. This document covers the essentials.

## Getting Started

1. Fork the repository and clone your fork.
2. Copy `.env.example` to `.env` and fill in the values.
3. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Development Workflow

- Work on a dedicated feature or fix branch — do not push directly to `main`.
- Use descriptive branch names: `feat/add-stats-endpoint`, `fix/async-db-session`.
- Keep commits small and focused. Write clear commit messages in imperative mood.

## Running Tests

```bash
python -m pytest tests/unit/         # Unit tests — run these before every commit
python -m pytest tests/integration/  # Integration tests — run before opening a PR
```

All unit tests must pass before opening a pull request. Integration tests require a running database; see `.env.example` for the `DATABASE_URL` configuration.

## Pull Requests

- Open a PR against `main`.
- Describe what you changed and why — include any relevant ticket or issue number.
- If the PR changes API behavior, update the relevant `docs/` file.
- At least one reviewer approval is required before merging.

## Code Style

- Python: formatted with `black`, linted with `ruff`. Config is in `pyproject.toml`.
- Run `black .` and `ruff check .` before committing.

## Sensitive Data

Never commit secrets, credentials, or API keys. All environment values must go in `.env` (which is gitignored). The `.env.example` file documents the required variables.

## Questions

Open an issue or reach out to the project maintainer directly.
