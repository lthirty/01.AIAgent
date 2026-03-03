# Multi-role Agent Console

本项目提供本地网页控制台 + Python 后端服务，支持多角色 Agent 分析与协作。

## 当前版本

- `v1.3.0`（2026-03-03）

## 版本管理规则

- 每次功能更新必须同步更新版本号。
- 每次提交发布改动时必须补充对应版本修改说明（`README.md` + `CHANGELOG.md`）。

## 版本说明

- `v1.3.0`
  - `Design/Test` 拆分为三个角色：`SCH design`、`PCB design`、`test`。
  - 页面中不同角色使用不同卡通人物配色展示。
- `v1.2.0`
  - 新增 `PM（产品经理）` 角色，支持单角色运行与协作讨论。
  - 前端增加 `运行 PM` 按钮与 PM 动画角色。
- `v1.1.0`
  - 登录密码调整为 `admin`。
  - 登录成功后在标题右侧显示当前用户名。
  - 登录成功后账号输入框、密码输入框、登录按钮置灰并禁用。
- `v1.0.0`
  - 初始版本：登录鉴权、单角色分析、多角色协作、结果输出。

详细记录见 `CHANGELOG.md`。

## 功能

- 单角色执行：`CTO` / `PM` / `SCH design` / `PCB design` / `test` / `DFM` / `Risk` / `Review`
- 多角色协作讨论：自动多轮讨论并生成联合结论
- 每次执行输出 Markdown 到 `outputs/`
- 登录鉴权：账号密码 + token 会话

## 启动方式

- 本机访问：`启动Agent控制台.bat`
- 局域网访问：`启动Agent控制台_局域网登录.bat`
- 远程访问（Cloudflare）：`启动Agent控制台_远程登录_Cloudflare.bat`

## 默认登录信息

- 用户名：`admin`
- 密码：`admin`

## API

- `POST /api/login`
- `POST /api/run-agent`
- `POST /api/run-collaboration`
- `POST /api/test-llm`
- `GET /api/results`
- `GET /outputs/<filename>?t=<token>`
