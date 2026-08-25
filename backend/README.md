# Backend v1

Minimal API scaffold for the future schedule service.

This branch is intentionally isolated from the production GitHub Pages application.

## API scope

- `GET /api/v1/health`
- `GET /api/v1/groups`
- `GET /api/v1/groups/{group_id}/schedule`
- `GET /api/v1/groups/{group_id}/changes`

The API is read-only from the HTTP side. Runtime schedule updates are performed by the sync worker, not by a public mutation endpoint.

## Data flow

`RUZ API -> backend/ruz_client.py -> backend/sync.py -> SQLite -> FastAPI`

The existing JSON files are bootstrap data for a fresh SQLite database. After SQLite has been populated, application restarts do not overwrite runtime data with the JSON snapshot.

The RUZ source currently used by the project is `https://ruz.fa.ru/api/schedule/group/{group_id}` with `start`, `finish`, and `lng=1` parameters. The client preserves the existing filtering rules for deleted lessons and repeated intermediate assessment entries.

## Synchronization

Synchronize all groups for the next 70 days:

```bash
python -m backend.sync
```

Synchronize one group:

```bash
python -m backend.sync --group-id 164606
```

Use a different horizon:

```bash
python -m backend.sync --days 30
```

The sync uses retries and concurrent requests. A failed group is left unchanged in SQLite; a partial sync does not delete other groups. A full successful sync may prune schedule/group records that are no longer present in `groups.json`.

## Persistent storage

The application uses `SCHEDULE_DB_PATH` for the SQLite location. The container defaults this to `/data/ruz_schedule.db`, so a production deployment must mount a persistent volume at `/data`.

Local development can use a project-local database, for example:

```bash
SCHEDULE_DB_PATH=./ruz_schedule.db uvicorn backend.app:app --reload
```

The repository contains `backend/Dockerfile` for a separate backend deployment. GitHub Pages remains the frontend host; the backend must be deployed separately with persistent storage.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
SCHEDULE_DB_PATH=./ruz_schedule.db uvicorn backend.app:app --reload
```

The API is intentionally not connected to the existing frontend yet. The migration will happen only after API/static data parity and the runtime synchronization path are verified.
