# Multi-role Agent Console

本项目提供本地网页控制台 + Python 后端服务，支持：

- 单角色执行：`CTO` / `Design/Test` / `DFM` / `Risk` / `Review`
- 多角色协作讨论：自动两轮讨论并生成最终联合结论
- 每次执行输出 Markdown 到 `outputs/`
- 登录鉴权（账号密码 + token 会话）

## 一键启动脚本

- 本机访问：`启动Agent控制台.bat`
- 局域网访问：`启动Agent控制台_局域网登录.bat`
- 跨网络远程访问（家里/办公室）：`启动Agent控制台_远程登录_Cloudflare.bat`

## 家里和办公室都能访问（推荐）

使用 `启动Agent控制台_远程登录_Cloudflare.bat`：

1. 安装 `cloudflared` 并加入 PATH
2. 双击脚本
3. 终端会显示一个 `https://xxxxx.trycloudflare.com` 地址
4. 家里和办公室都可打开该地址登录使用

## 默认登录信息

脚本默认：

- 用户名：`admin`
- 密码：`ChangeMe_2026`

建议你立即改脚本里的 `WEB_PASSWORD`。

## 模型配置（已写入脚本）

脚本已内置：

- `LLM_PROVIDER=minimax`
- `MINIMAX_MODEL=MiniMax-M2.5`
- `MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic`

## API

- `POST /api/login`
- `POST /api/run-agent`
- `POST /api/run-collaboration`
- `POST /api/test-llm`
- `GET /api/results`
- `GET /outputs/<filename>?t=<token>`
