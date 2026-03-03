# Changelog

## v1.7.0 - 2026-03-03

- Added cloud deployment support with Docker artifacts:
  - `Dockerfile`
  - `.dockerignore`
  - `requirements.txt`
- Backend now supports `HOST` and `PORT` environment variables for cloud platforms.
- Added health check endpoint: `GET /api/health`.
- Updated README with cloud deployment and cross-location access instructions.

## v1.6.0 - 2026-03-03

- Enforced Chinese-only output in role reports and collaboration reports.
- Added automatic web research context before agent generation.
- Added PDF parsing for uploaded materials (`pypdf`, with auto-install fallback).
- Refined role execution prompts, especially:
  - `SCH design`: key module/signal schematic constraints and checks
  - `PCB design`: stackup/routing/EMI/SI-PI design constraints
- Added stronger constraint: if datasheet parameters are unknown, output must provide:
  - parameter confirmation checklist
  - temporary design assumptions

## v1.5.0 - 2026-03-03

- Added persistent project sessions (`projects.json`).
- Added project APIs:
  - `GET /api/projects`
  - `GET /api/projects/<id>`
  - `POST /api/projects/save`
- Added frontend project workflow:
  - Create/save project
  - Select and load historical project
  - View per-project discussion history
- `run-agent` and `run-collaboration` now bind outputs to `projectId`.

## v1.4.0 - 2026-03-03

- Improved collaboration markdown readability.
- Moved conclusion to Chapter 1.
- Each round is now a separate chapter with a round summary.

## v1.3.0 - 2026-03-03

- Split `Design/Test` into:
  - `SCH design`
  - `PCB design`
  - `test`
- Added distinct cartoon avatar styles per role.

## v1.2.0 - 2026-03-03

- Added `PM` role.

## v1.1.0 - 2026-03-03

- Login password changed to `admin`.
- Show logged-in username on the right side of title.
- Disable login controls after successful login.

## v1.0.0 - 2026-03-03

- Initial release.
