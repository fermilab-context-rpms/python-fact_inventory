# Fact Inventory

A lightweight API service built with Litestar for collecting and storing system
information from remote hosts. Designed to handle large-scale concurrency, the
service receives HTTP submissions of system facts and package inventory from
Ansible, curl, or other client tooling.

## Features

- **Rate Limiting**: Per-IP rate limiting
- **Automatic Data Retention**: Background task purges records older than `RETENTION_DAYS`
- **Duplicate Fact Pruning**: Keeps the newest `HISTORY_MAX_ENTRIES` per client
- **Async Architecture**: SQLAlchemy async and Litestar for high-performance concurrent handling
- **Type Safety**: Full type annotations, Pydantic validation, mypy strict mode
- **Flexible Storage**: Arbitrary JSON data for system, package, and local facts
- **Payload Limits**: Per-field and total request body size limits
- **PostgreSQL Optimized**: `JSONB` fields with `GIN` indexes; SQLite support for development
- **Health/Readiness Probes**: Built-in endpoints for container orchestration

## Getting Started

Choose the path that matches your role:

- **Running locally for development**: See [DEVELOPMENT.md](DEVELOPMENT.md)
- **Installing for production**: See [INSTALL.md](INSTALL.md)
- **Deploying to bare metal, Kubernetes, or embedding**: See [DEPLOYMENT.md](DEPLOYMENT.md)

## Architecture Overview

The application runs as a stateless ASGI service. In production, a reverse proxy
(nginx, Apache, or Kubernetes Ingress) strips the `/fact_inventory` prefix before
forwarding requests to the application. This design supports three deployment modes:

1. **Bare metal**: Uvicorn + reverse proxy (nginx/Apache)
2. **Kubernetes**: Uvicorn in container + Ingress controller
3. **Embedded**: Mounted as a sub-router in a parent Litestar application

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed setup instructions for each scenario.

## Background Tasks

**Data Retention**
Purges records older than `RETENTION_DAYS`. Runs every `RETENTION_CHECK_INTERVAL_HOURS`
plus random jitter.

**Duplicate Pruning**
Removes duplicates per `client_address`, keeping the newest `HISTORY_MAX_ENTRIES`.
Runs every `HISTORY_CHECK_INTERVAL_HOURS` plus random jitter.

Both tasks defer their first run until after the initial interval to avoid impacting startup.

## Security Model

- No client authentication or network restrictions
- Rate limiting by IP address (can be bypassed with IP rotation)
- Per-field and total request body size limits prevent DoS attacks
- Required fields are mandatory; unknown fields rejected
- CORS disabled (clients are server-side scripts, not browsers)
- CSRF protection not needed (no sessions or cookies)

## Querying Data

With `GIN` indexes on `JSONB` fields, you can efficiently query and build views.
See [VIEWS.md](VIEWS.md) for ready-to-use `CREATE VIEW` examples covering:

- Host overview
- Package inventory
- Distribution summary
- Stale host detection

## Example Client

See the example playbook `gather.yml` for more information.
