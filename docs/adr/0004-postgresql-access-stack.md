---
status: accepted
---

# PostgreSQL access goes through psycopg 3, SQLAlchemy's typed ORM, and reviewed Alembic migrations

The handoff fixes PostgreSQL with pgvector and full-text search but defers the driver, query layer, and migration tool. We use **psycopg 3** (`psycopg[binary,pool]`, async mode at runtime) as the only PostgreSQL driver, **SQLAlchemy 2.x typed declarative ORM** (`Mapped[]`) for persistence models with hand-written textual SQL for hybrid, full-text, and exact-identifier search, and **Alembic** for schema migrations. SQLAlchemy is pinned to the 2.0 line until 2.1 is final.

A reader may wonder why an ORM sits under a codebase whose every other model is Pydantic. The handoff lists around twenty related persistent entities; mapping them by hand over a bare driver is more code than agents can keep consistent, and Alembic's model-aware diffing only works with SQLAlchemy metadata. We rejected **SQLModel** because it merges the Pydantic contract and the table into one class, which is exactly the "persistence models stay distinct from public contracts" rule we must enforce, and it pins below SQLAlchemy 2.1. We rejected **asyncpg** not on quality but because it would make psycopg a second driver for Alembic and synchronous scripts, and SQLAlchemy 2.1 makes psycopg 3 its default PostgreSQL driver anyway.

## Consequences

- Three kinds of model, defined in `CONTEXT.md`: public contracts (Pydantic, at the MCP/REST/CLI boundary), domain types (what services and predicates operate on), and persistence models (SQLAlchemy, infrastructure only). Repositories accept and return domain types; a persistence model never crosses the infrastructure boundary, and CI enforces that SQLAlchemy is imported only under the infrastructure package.
- Migrations are the schema. Alembic autogenerate may produce a draft, but every migration is reviewed and committed, and CI fails when the models and the head migration disagree. Migrations run only through an explicit CLI command, never on service start. Tests build their schema by migrating to head, never with `create_all`.
- Tests that touch the database run against a real PostgreSQL 17 with pgvector (a Compose service locally, a service container in GitHub Actions). Domain and predicate tests never touch the database.
- Hybrid search stays as reviewed SQL in the knowledge repository rather than ORM expressions, so the exact query the planner sees is the one in the file.
- The strict type checker is not part of this decision (it is cheap to swap): pyright semantics in strict mode, installed as `basedpyright` so `uv` needs no system Node, with Astral's `ty` noted for reconsideration at its 1.0.
- Evidence for versions and support claims at decision time (2026-09-22): psycopg 3.3.6, SQLAlchemy 2.0.54 stable with 2.1.0rc2, Alembic 1.20.0, pgvector 0.5.0 (asyncpg, psycopg 3, SQLAlchemy). Details in [map ticket #19](https://github.com/andrewferk/opnsense-pilot/issues/19).
