# Multi-role Agent Console

Web console + Python backend for multi-role agent analysis and collaboration.

## Current Version

- `v1.5.0` (2026-03-03)

## Version Rule

- Every update must bump the version.
- Every update must include version notes in both `README.md` and `CHANGELOG.md`.

## Version Notes

- `v1.5.0`
  - Added persistent project sessions and discussion history.
  - You can reopen and continue an existing project (for example, Project A).
  - You can also create a new project (for example, Project B).
- `v1.4.0`
  - Improved collaboration markdown readability.
  - Final conclusion moved to Chapter 1.
  - Each discussion round is now its own chapter with a round summary.
- `v1.3.0`
  - Split `Design/Test` into `SCH design`, `PCB design`, and `test`.
  - Different cartoon avatar styles for different roles.
- `v1.2.0`
  - Added `PM` role.
- `v1.1.0`
  - Login password set to `admin`.
  - Show current username after login.
  - Disable username/password/login controls after login.
- `v1.0.0`
  - Initial release.

## Features

- Single-role run: `CTO` / `PM` / `SCH design` / `PCB design` / `test` / `DFM` / `Risk` / `Review`
- Multi-role collaboration report output to `outputs/`
- Login auth with token session
- Persistent project list and project-level discussion history

## Start

- Local: `启动Agent控制台.bat`
- LAN: `启动Agent控制台_局域网登录.bat`
- Remote: `启动Agent控制台_远程登录_Cloudflare.bat`

## Default Login

- Username: `admin`
- Password: `admin`

## APIs

- `POST /api/login`
- `GET /api/projects`
- `GET /api/projects/<id>`
- `POST /api/projects/save`
- `POST /api/run-agent`
- `POST /api/run-collaboration`
- `GET /api/results`

