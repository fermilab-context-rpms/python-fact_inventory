# Development

## Development Dependencies

Install with development dependencies:

```bash
uv sync --group dev
```

Install the pre-commit hooks once after cloning:

```bash
uv run pre-commit install
```

## Running the Application

The application requires the `DEPLOYMENT` environment variable to be set.

For development, use `DEPLOYMENT=testing`:

```bash
export DEPLOYMENT=testing
uv run litestar --app fact_inventory:app database upgrade
uv run python -m fact_inventory
```

Or once the database is setup:

```bash
DEPLOYMENT=testing uv run python -m fact_inventory
```

## Testing

Run all tests:

```bash
uv run pytest
```

Test utilities in `tests/factories/` and `tests/assertions.py` provide helpers for payloads, models,
and common assertions.

## Debug Mode

Enable debug mode to access OpenAPI documentation:

```bash
export DEBUG=true
```

Visit `http://localhost:8000/fact_inventory/schema` for the OpenAPI spec or
`http://localhost:8000/fact_inventory/schema/swagger` for a UI.

## Code Quality Tools

The project uses pre-commit hooks for code quality:

- ruff: Fast Python linter and formatter
- mypy: Static type checking
- pyright: Static type checking
- pre-commit-hooks: Standard checks (trailing whitespace, merge conflicts, etc.)
- prettier: Standardize various documentation formatting

Run checks manually:

```bash
# Run all pre-commit hooks against every file
uv run pre-commit run --all-files

# Run ruff
uv run ruff check .
uv run ruff format .

# Run mypy
uv run mypy fact_inventory

# Run pyright
uv run pyright fact_inventory
```

## Pre-commit Hook Failures

If commits are blocked by pre-commit:

```bash
# Fix issues automatically where possible
uv run pre-commit run --all-files

# Skip hooks in emergency (not recommended)
git commit --no-verify
```
