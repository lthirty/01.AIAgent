# Multi-role Agent Console

多角色 Agent 协作控制台（网页前端 + Python 后端）。

## 当前版本

- `v1.7.0`（2026-03-03）

## 版本规则

- 每次更新必须同步更新版本号。
- 每次更新必须在 `README.md` 和 `CHANGELOG.md` 同步记录修改说明。

## 版本说明（最新）

- `v1.7.0`
  - 新增云部署能力：支持 Docker 化部署到云服务器。
  - 后端支持读取 `HOST`/`PORT` 环境变量，适配云平台动态端口。
  - 新增健康检查接口：`GET /api/health`。
  - 新增 `Dockerfile` / `.dockerignore` / `requirements.txt`。
- `v1.6.0`
  - 全角色输出强制中文。
  - 增加联网检索上下文（自动补充）。
  - 增加 PDF 解析（含 `pypdf` 自动安装兜底）。
  - 强化 SCH / PCB 角色设计细节要求。

## 主要功能

- 单角色执行：`CTO` / `PM` / `SCH design` / `PCB design` / `test` / `DFM` / `Risk` / `Review`
- 多角色协作输出：`outputs/*.md`
- 项目历史可持久化：支持继续历史项目讨论
- 资料上传支持 PDF 文本提取
- 自动联网检索补充设计上下文

## 本地启动

- 本机：`启动Agent控制台.bat`
- 局域网：`启动Agent控制台_局域网登录.bat`
- 跨网远程（Cloudflare）：`启动Agent控制台_远程登录_Cloudflare.bat`

## 云部署（Docker）

1. 准备云服务器（Ubuntu/CentOS 均可），确保 22 端口可 SSH 登录。  
2. 安装 Docker（示例 Ubuntu）：

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
```

3. 拉取代码并进入项目目录：

```bash
git clone <你的仓库地址>
cd 01.AIAgent
```

4. 构建镜像：

```bash
docker build -t ai-agent-console:latest .
```

5. 启动容器（示例映射到 8787）：

```bash
docker run -d \
  --name ai-agent-console \
  --restart unless-stopped \
  -p 8787:8787 \
  -e HOST=0.0.0.0 \
  -e PORT=8787 \
  -e WEB_USERNAME=admin \
  -e WEB_PASSWORD=admin \
  ai-agent-console:latest
```

6. 健康检查：

```bash
curl http://<云服务器IP>:8787/api/health
```

返回 `{"ok": true, "status": "healthy"}` 即部署成功。

## 跨地点访问（推荐）

- 方式 A：开放云服务器 `8787` 端口，并用 `http://<云服务器公网IP>:8787` 访问。
- 方式 B（更安全）：在云服务器部署 Cloudflare Tunnel，仅暴露 Cloudflare 域名，不直接开放 8787 端口。

## 默认登录

- 用户名：`admin`
- 密码：`admin`

## API

- `GET /api/health`
- `POST /api/login`
- `GET /api/projects`
- `GET /api/projects/<id>`
- `POST /api/projects/save`
- `POST /api/run-agent`
- `POST /api/run-collaboration`
- `GET /api/results`

