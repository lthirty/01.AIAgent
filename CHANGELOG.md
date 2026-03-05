# Changelog

## v1.10.3 - 2026-03-05

- 修复动画背景亮度滑条生效问题：亮度变化改为直接驱动背景层（含 anim-zone 与 scene 背景）。
- 新增 change 事件兜底，确保不同浏览器下滑条调节都能触发。
## v1.10.2 - 2026-03-05

- 新增动画背景亮度滑条（70%~160%），可实时调节并本地持久化。
- 亮度调整仅作用于背景层，不影响人物/角色动画层。
- 保留浅蓝/浅绿主题按钮切换，与亮度滑条可叠加使用。
## v1.10.1 - 2026-03-05

- 主界面布局固定为 6:4（左侧控制台 : 右侧动画区），收缩/展开资料栏不再影响左右占比。
- 资料与结果区域改为默认展开，按钮切换为“收缩/展开资料与结果栏”。
- 动画背景亮度重构为“仅背景提亮”，不再影响人物层亮度。
- 动画背景改为亮色调，并新增按钮支持浅蓝/浅绿主题切换（默认浅蓝，状态本地持久化）。
## v1.10.0 - 2026-03-05

- Added a master toggle button for panel resizing:
  - 开启两栏缩放 / 锁定两栏大小
  - Controls both 上传资料 and 结果文件 panels together.
- Applied Star Office UI animation assets to the right-side scene:
  - Office background + worker sprite + syncing sprite.
  - Files copied into web/star-office/.
- Added static asset route support in backend:
  - GET /web/<relative_path> serves files under web/.
- Expanded page width and kept right-side animation area wider than left.

## v1.9.0 - 2026-03-03

- Added RK3588 project-specific reusable template:
  - `materials/templates/RK3588_SCH_PCB_瑙勫垯妯℃澘_v1.0.md`
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
  - `materials/templates/SCH_PCB_瑙勫垯妯℃澘_v1.0.md`
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




