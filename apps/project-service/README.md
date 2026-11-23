# Project Service

> [!NOTE]
> **Status: paused prototype.** This service comes from DesignSynapse's earlier service-oriented architecture and is not under active development. It corresponds to the **Project delivery** stage of the [platform vision](../../README.md#platform-vision) and will be integrated into the platform in a later phase. See the [main README](../../README.md) for the project's current scope.

**Project records and threaded discussion for DesignSynapse: a REST service for creating, tracking and commenting on building projects.**

## Capabilities

| Capability | Description |
|---|---|
| Project records | Create, retrieve, list, update and delete projects, each with a name, description, owner, visibility setting, archive flag and free-form metadata |
| Status workflow | Status changes through a dedicated endpoint, against a configurable status set (default: draft, in progress, review, completed, archived) |
| Threaded comments | Comments on a project, with replies linked to a parent comment |
| Authentication | Bearer-token (JWT) validation of requests, with users referenced by their identity-service ID |
| API versioning | Version negotiation through the `Accept` header (`application/vnd.design-synapse.v1+json`) |
| Operational endpoints | Liveness, readiness, detailed health and metrics |

## API

All routes are served under `/api/v1`.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/projects` | Create a project |
| `GET` | `/projects` | List projects |
| `GET` | `/projects/{project_id}` | Retrieve a project |
| `PUT` | `/projects/{project_id}` | Update a project |
| `PATCH` | `/projects/{project_id}/status` | Change a project's status |
| `DELETE` | `/projects/{project_id}` | Delete a project |
| `POST` | `/projects/{project_id}/comments` | Add a comment |
| `GET` | `/projects/{project_id}/comments` | List a project's comments |
| `GET` | `/projects/{project_id}/comments/{comment_id}` | Retrieve a comment |
| `PUT` | `/projects/{project_id}/comments/{comment_id}` | Edit a comment |
| `DELETE` | `/projects/{project_id}/comments/{comment_id}` | Delete a comment |
| `GET` | `/health`, `/ready`, `/health/detailed`, `/metrics` | Operational status |

## Technology

FastAPI, SQLAlchemy 2.0, Pydantic v2 and Alembic, backed by a MySQL-compatible database (TiDB) through PyMySQL. Service limits, such as the maximum projects per user and comment length, are set in [`src/core/config.py`](src/core/config.py).
