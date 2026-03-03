# Changelog

## v1.9.0 - 2026-03-03

- Added RK3588 project-specific reusable template:
  - `materials/templates/RK3588_SCH_PCB_规则模板_v1.0.md`
- Added fill-in tables for real project execution:
  - power rail table
  - clock planning table
  - boot/reset configuration table
  - DDR and high-speed interface constraints table
  - risk matrix and EVT/DVT verification table
- Updated role prompts for RK3588-first behavior:
  - `SCH design`: prefer RK3588 template when input includes RK3588/RK3588S
  - `PCB design`: prefer RK3588 template when input includes RK3588/RK3588S

## v1.8.0 - 2026-03-03

- Added reusable SCH/PCB rule template:
  - `materials/templates/SCH_PCB_规则模板_v1.0.md`
- Organized template by hardware modules for real-project reuse:
  - Power
  - Clock
  - Reset/Boot
  - High-speed interfaces (DDR/USB/PCIe/Ethernet)
  - EMC/ESD
  - Thermal
  - DFM/DFT
- Updated role prompts to enforce template-based outputs:
  - `SCH design`
  - `PCB design`
- Enforced structured deliverables in SCH/PCB outputs:
  - executable constraint table
  - risk matrix (P0/P1/P2)
  - verification plan (EVT/DVT)
  - pending information checklist

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
