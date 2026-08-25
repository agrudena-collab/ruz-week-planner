# Backend v1

Minimal API scaffold for the future schedule service.

This branch is intentionally isolated from the production GitHub Pages application.

## Scope

- `GET /api/v1/health`
- `GET /api/v1/groups`
- `GET /api/v1/groups/{group_id}/schedule`
- `GET /api/v1/groups/{group_id}/changes`

The first implementation is read-only and uses a local SQLite database for development. It does not contain authentication, payments, notifications, or secrets.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

The API is intentionally not connected to the existing frontend yet. The migration will happen only after API/static data parity is verified.
