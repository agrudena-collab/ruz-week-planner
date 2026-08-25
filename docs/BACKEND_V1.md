# Backend v1 architecture

## Purpose

Introduce a small API/database layer without breaking the current static GitHub Pages application.

The current GitHub Actions pipeline remains the source of imported RUZ data during the migration. The backend is a new canonical application-data layer for the future user accounts and notifications.

## Phase 1 scope

Backend v1 should support only:

- groups;
- current schedules by group;
- detected schedule changes by group;
- a read-only public API;
- synchronization from the existing GitHub Actions pipeline.

Out of scope for v1:

- registration/authentication;
- personal accounts;
- subscriptions/payments;
- push/email/Telegram notifications;
- admin UI.

## Logical model

### groups

- `id` — RUZ group ID, primary key
- `name` — group name
- `updated_at` — last catalog update
- `is_active` — whether the group is currently available in RUZ

### schedule_lessons

- `id` — internal primary key
- `group_id` — foreign key to `groups.id`
- `date`
- `lesson_number_start`
- `lesson_number_end`
- `sub_group`
- `stream`
- `begin_lesson`
- `end_lesson`
- `discipline`
- `lecturer`
- `auditorium`
- `building`
- `kind_of_work`
- `updated_at`

A unique constraint should identify one stable lesson slot by group/date/lesson numbers/subgroup/stream, matching the existing change-detector identity.

### schedule_changes

- `id` — internal primary key
- `group_id` — foreign key to `groups.id`
- `lesson_slot_key`
- `detected_at`
- `change_type` — added/removed/updated
- `payload` — JSON describing changed fields and old/new values

## API v1

Public read-only endpoints:

- `GET /api/v1/groups`
- `GET /api/v1/groups/{group_id}/schedule`
- `GET /api/v1/groups/{group_id}/changes`
- `GET /api/v1/health`

Responses should be JSON and include explicit versioning under `/api/v1/`.

## Synchronization

The existing GitHub Actions workflow remains responsible for downloading and validating RUZ data. After successful validation it will eventually call an authenticated backend ingestion endpoint or upload an artifact consumed by a backend worker.

The first backend integration must be additive: failure to synchronize with the backend must not prevent the current GitHub Pages deployment while the migration is in progress.

Recommended sequence:

1. fetch RUZ data;
2. validate all groups and schedules;
3. publish current static files as today;
4. attempt backend synchronization;
5. record synchronization status;
6. continue deployment even if backend synchronization is temporarily unavailable.

## Frontend migration

Do not switch `index.html` from JSON to API in the first backend commit.

Migration should be staged:

1. deploy API and database;
2. mirror existing data into the API;
3. add API read support behind a feature flag or safe fallback;
4. compare API results with static JSON;
5. switch the frontend to API only after parity is verified;
6. keep static JSON as a temporary fallback during rollout.

## Security requirements for later implementation

- ingestion endpoint must require authentication;
- secrets must be stored outside the repository;
- validate group IDs and payload schemas server-side;
- rate-limit public endpoints;
- use parameterized database queries/ORM;
- never expose database credentials to the frontend;
- enable structured logging and health checks.

## Deployment principle

The backend must be deployed separately from GitHub Pages. GitHub Pages remains the static frontend host. The backend should have its own deployment, database, secrets, logs, and health monitoring.
