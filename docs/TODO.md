# TODO

Outstanding work items. Not prioritized; items should be evaluated against
use-case requirements before implementation.

## Application

- [ ] Add distributed rate-limit state (Redis or similar) for multi-instance
      deployments that require rate-limit persistence across restarts
- [ ] Implement authentication/authorization if clients require identity
      (currently network-level security only)
- [ ] Enforce a per-statement database timeout for retention deletes. The
      previous `.execution_options(timeout=...)` was a silent no-op and has
      been removed; no statement cap is currently enforced. Intended design:
      apply `SET LOCAL statement_timeout` at the start of each retention batch
      transaction (PostgreSQL-only), driven by a new `db_statement_timeout_ms`
      setting (default 60000).

## Observability

- [ ] Add custom Prometheus metrics (cleanup duration, fact sizes, rate-limit
      violations)

## Repository

- [ ] Set up CI to verify compatibility with latest `advanced-alchemy`,
      `litestar`, and `sqlalchemy` releases
