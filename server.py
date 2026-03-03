#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import cgi
import datetime as dt
import json
import os
import re
import secrets
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, parse, request

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
OUTPUT_DIR = BASE_DIR / "outputs"
MATERIAL_DIR = BASE_DIR / "materials"
ROLE_PROMPTS_PATH = BASE_DIR / "role_prompts.json"

OUTPUT_DIR.mkdir(exist_ok=True)
MATERIAL_DIR.mkdir(exist_ok=True)

ROLES = ["CTO", "Design/Test", "DFM", "Risk", "Review"]
DEFAULT_ROLE_PROMPTS = {
    "CTO": "你是 CTO，请从技术路线、架构演进、成本和里程碑角度给出建议。",
    "Design/Test": "你是 Design/Test 负责人，请从可测试性、测试覆盖、验证计划和质量门控角度给出建议。",
    "DFM": "你是 DFM 负责人，请从可制造性、工艺窗口、BOM 风险、量产导入角度给出建议。",
    "Risk": "你是 Risk 负责人，请识别风险并评估概率/影响，提出缓解措施和触发条件。",
    "Review": "你是 Review 主持人，请整合各角色观点，给出冲突点、决策建议和下一步行动。",
}

AUTH_USERNAME = os.getenv("WEB_USERNAME", "admin").strip()
AUTH_PASSWORD = "admin"
AUTH_ENABLED = os.getenv("WEB_AUTH_ENABLED", "1").strip() != "0"
TOKEN_TTL_SECONDS = int(os.getenv("WEB_TOKEN_TTL_SECONDS", "43200"))
SESSIONS = {}


def now_ts() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name)


def clean_sessions() -> None:
    now = dt.datetime.now().timestamp()
    expired = [k for k, v in SESSIONS.items() if v < now]
    for k in expired:
        SESSIONS.pop(k, None)


def list_markdown_files():
    files = sorted(OUTPUT_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {
            "name": p.name,
            "size": p.stat().st_size,
            "mtime": dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
            "url": f"/outputs/{p.name}",
        }
        for p in files
    ]


def list_material_files():
    files = sorted(MATERIAL_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in files:
        if not p.is_file():
            continue
        out.append(
            {
                "id": p.name,
                "name": p.name,
                "size": p.stat().st_size,
                "mtime": dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
                "url": f"/materials/{parse.quote(p.name)}",
            }
        )
    return out


def load_role_prompts() -> dict:
    if not ROLE_PROMPTS_PATH.exists():
        return dict(DEFAULT_ROLE_PROMPTS)
    try:
        data = json.loads(ROLE_PROMPTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_ROLE_PROMPTS)
    prompts = dict(DEFAULT_ROLE_PROMPTS)
    for role in ROLES:
        if isinstance(data.get(role), str) and data[role].strip():
            prompts[role] = data[role].strip()
    return prompts


def save_role_prompts(prompts: dict) -> None:
    payload = {role: prompts.get(role, DEFAULT_ROLE_PROMPTS[role]) for role in ROLES}
    ROLE_PROMPTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


ROLE_PROMPTS = load_role_prompts()


def load_material_text(material_id: str) -> str:
    target = (MATERIAL_DIR / Path(material_id).name).resolve()
    if target.parent != MATERIAL_DIR.resolve() or not target.exists() or not target.is_file():
        return ""
    text_ext = {".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".log", ".py", ".js", ".ts", ".html", ".css"}
    if target.suffix.lower() not in text_ext:
        return f"[文件 {target.name} 为非文本格式，已附带文件名供参考]"
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = target.read_text(encoding="gbk", errors="ignore")
    return content[:12000]


def merge_product_definition(product_definition: str, material_ids) -> str:
    base = product_definition.strip()
    material_ids = material_ids or []
    if not material_ids:
        return base
    sections = [base, "\n\n---\n\n## 参考资料\n"]
    for idx, material_id in enumerate(material_ids, start=1):
        content = load_material_text(material_id)
        if not content:
            continue
        sections.extend(
            [
                f"\n### 资料 {idx}: {Path(material_id).name}\n",
                "```text\n",
                content,
                "\n```\n",
            ]
        )
    return "".join(sections).strip()


class LLM:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "auto").strip().lower()

        self.minimax_api_key = os.getenv("MINIMAX_API_KEY", "").strip()
        self.minimax_model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5").strip()
        self.minimax_base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic").strip()

        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com").strip()

        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1200"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.4"))

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        errors = []
        prefer_minimax = self.provider in ("auto", "minimax")
        prefer_openai = self.provider in ("auto", "openai")

        if prefer_minimax and self.minimax_api_key:
            try:
                return self._minimax_messages(system_prompt, user_prompt)
            except Exception as e:
                errors.append(f"minimax: {e}")

        if prefer_openai and self.openai_api_key:
            try:
                return self._openai_chat(system_prompt, user_prompt)
            except Exception as e:
                errors.append(f"openai: {e}")

        return self._fallback(system_prompt, user_prompt, errors)

    def test_connection(self) -> dict:
        errors = []

        if self.provider in ("auto", "minimax"):
            if not self.minimax_api_key:
                errors.append("minimax: MINIMAX_API_KEY 未设置")
            else:
                try:
                    text = self._minimax_messages("You are a connectivity checker.", "Reply with one line: minimax ok.")
                    return {"provider": "minimax", "model": self.minimax_model, "preview": text[:500]}
                except Exception as e:
                    errors.append(f"minimax: {e}")

        if self.provider in ("auto", "openai"):
            if not self.openai_api_key:
                errors.append("openai: OPENAI_API_KEY 未设置")
            else:
                try:
                    text = self._openai_chat("You are a connectivity checker.", "Reply with one line: openai ok.")
                    return {"provider": "openai", "model": self.openai_model, "preview": text[:500]}
                except Exception as e:
                    errors.append(f"openai: {e}")

        raise RuntimeError(" | ".join(errors) if errors else "未配置可用模型提供方")

    def _minimax_messages(self, system_prompt: str, user_prompt: str) -> str:
        endpoint = self.minimax_base_url.rstrip("/") + "/v1/messages"
        payload = {
            "model": self.minimax_model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            endpoint,
            data=data,
            method="POST",
            headers={
                "x-api-key": self.minimax_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        with request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        blocks = body.get("content", [])
        texts = []
        for block in blocks:
            btype = block.get("type")
            if btype == "thinking" and block.get("thinking"):
                texts.append(f"[Thinking]\n{block['thinking']}")
            if btype == "text" and block.get("text"):
                texts.append(block["text"])

        if texts:
            return "\n\n".join(texts).strip()
        if "output_text" in body:
            return str(body["output_text"]).strip()
        return json.dumps(body, ensure_ascii=False, indent=2)

    def _openai_chat(self, system_prompt: str, user_prompt: str) -> str:
        endpoint = self.openai_base_url.rstrip("/") + "/v1/chat/completions"
        payload = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            endpoint,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            },
        )
        with request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()

    def _fallback(self, system_prompt: str, user_prompt: str, errors=None) -> str:
        err_text = "; ".join(errors or [])
        lines = [
            "## 自动分析（离线模板）",
            "",
            f"- 角色指令: {system_prompt}",
            "- 说明: 未检测到可用 API Key 或远程调用失败，当前使用本地模板输出。",
        ]
        if err_text:
            lines.append(f"- 失败原因: {err_text}")

        lines.extend(
            [
                "",
                "## 结论摘要",
                "- 目标澄清: 将产品定义转为可执行需求、约束与验收指标。",
                "- 关键动作: 拆分阶段里程碑，明确 owner、截止时间和度量方法。",
                "",
                "## 建议行动",
                "1. 列出 Top 5 需求与不可妥协约束。",
                "2. 为每条需求定义量化验收标准。",
                "3. 设立每周风险复盘与跨角色评审。",
                "",
                "## 输入摘录",
                "```text",
                user_prompt[:2000],
                "```",
            ]
        )
        return "\n".join(lines)


class AgentService:
    def __init__(self):
        self.llm = LLM()

    def run_single(self, role: str, product_definition: str):
        if role not in ROLES:
            raise ValueError(f"Unknown role: {role}")
        system = ROLE_PROMPTS[role]
        user = (
            "以下是产品定义，请输出 markdown，包含：结论摘要、关键问题、建议、下一步行动。\n\n"
            f"{product_definition.strip()}"
        )
        content = self.llm.generate(system, user)
        title = f"# {role} Agent 输出\n\n- 时间: {dt.datetime.now().isoformat(timespec='seconds')}\n\n"
        final_md = title + content + "\n"
        filename = f"{now_ts()}_{slugify(role)}.md"
        (OUTPUT_DIR / filename).write_text(final_md, encoding="utf-8")
        return filename, final_md

    def run_collaboration(self, product_definition: str):
        rounds = []

        initial = {}
        for role in ROLES:
            prompt = (
                "你将参与跨职能评审。先独立给出观点。输出 markdown，包含：立场、发现、建议、阻塞项。\n\n"
                f"产品定义:\n{product_definition.strip()}"
            )
            initial[role] = self.llm.generate(ROLE_PROMPTS[role], prompt)
        rounds.append(("Round 1", initial))

        discussion = {}
        digest = "\n\n".join([f"### {r}\n{initial[r][:2500]}" for r in ROLES])
        for role in ROLES:
            prompt = (
                "请基于以下其他角色观点进行回应与协同，输出 markdown，包含：认同点、分歧点、需验证假设、行动项。\n\n"
                f"产品定义:\n{product_definition.strip()}\n\n"
                f"跨角色观点摘要:\n{digest}"
            )
            discussion[role] = self.llm.generate(ROLE_PROMPTS[role], prompt)
        rounds.append(("Round 2", discussion))

        synthesis_input = "\n\n".join(
            [f"## {label} - {role}\n{content[:3000]}" for label, data in rounds for role, content in data.items()]
        )
        final = self.llm.generate(
            ROLE_PROMPTS["Review"],
            "请输出最终联合结论（markdown），包含：最终决策、风险闭环、里程碑、责任分配(RACI)、本周行动清单。\n\n"
            f"产品定义:\n{product_definition.strip()}\n\n"
            f"讨论记录:\n{synthesis_input}",
        )

        out = [
            "# 多角色协作报告",
            "",
            f"- 时间: {dt.datetime.now().isoformat(timespec='seconds')}",
            "",
            "## 产品定义",
            "```text",
            product_definition.strip(),
            "```",
            "",
        ]

        for label, data in rounds:
            out.append(f"## {label}")
            out.append("")
            for role in ROLES:
                out.append(f"### {role}")
                out.append("")
                out.append(data[role])
                out.append("")

        out.append("## Final Synthesis")
        out.append("")
        out.append(final)
        out.append("")

        final_md = "\n".join(out)
        filename = f"{now_ts()}_collaboration.md"
        (OUTPUT_DIR / filename).write_text(final_md, encoding="utf-8")
        return filename, final_md

    def test_llm(self) -> dict:
        return self.llm.test_connection()


class Handler(BaseHTTPRequestHandler):
    service = AgentService()

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, status: int, text: str, content_type: str = "text/plain; charset=utf-8"):
        body = text.encode("utf-8", errors="replace")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, status: int, payload: bytes, content_type: str = "application/octet-stream"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _get_token(self):
        token = self.headers.get("X-Access-Token", "").strip()
        if token:
            return token
        auth = self.headers.get("Authorization", "").strip()
        if auth.startswith("Bearer "):
            return auth[7:].strip()
        parsed = parse.urlparse(self.path)
        q = parse.parse_qs(parsed.query)
        t = (q.get("t") or [""])[0].strip()
        return t

    def _authorized(self) -> bool:
        if not AUTH_ENABLED:
            return True
        clean_sessions()
        token = self._get_token()
        return token in SESSIONS

    def _need_auth(self, path: str) -> bool:
        if not AUTH_ENABLED:
            return False
        if path in ["/", "/index.html", "/api/login"]:
            return False
        if path.startswith("/api/") or path.startswith("/outputs/") or path.startswith("/materials/"):
            return True
        return False

    def _save_uploaded_material(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
        )
        if "file" not in form:
            raise ValueError("missing file field")
        file_item = form["file"]
        if not getattr(file_item, "filename", ""):
            raise ValueError("empty filename")
        original = Path(file_item.filename).name
        stem = slugify(Path(original).stem)[:80] or "material"
        ext = Path(original).suffix[:12]
        target_name = f"{now_ts()}_{stem}{ext}"
        target = MATERIAL_DIR / target_name
        data = file_item.file.read()
        if not data:
            raise ValueError("empty file content")
        target.write_bytes(data)
        return target_name

    def do_GET(self):
        try:
            path = parse.urlparse(self.path).path
            if self._need_auth(path) and not self._authorized():
                self._json(401, {"ok": False, "error": "Unauthorized"})
                return

            if path in ["/", "/index.html"]:
                html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
                self._text(200, html, "text/html; charset=utf-8")
                return

            if path == "/api/results":
                self._json(200, {"ok": True, "results": list_markdown_files()})
                return

            if path == "/api/materials":
                self._json(200, {"ok": True, "materials": list_material_files()})
                return

            if path == "/api/roles":
                self._json(200, {"ok": True, "roles": ROLES, "prompts": ROLE_PROMPTS})
                return

            if path == "/api/auth-info":
                self._json(200, {"ok": True, "authEnabled": AUTH_ENABLED})
                return

            if path.startswith("/outputs/"):
                name = parse.unquote(path.replace("/outputs/", "", 1))
                safe = Path(name).name
                target = OUTPUT_DIR / safe
                if target.exists() and target.is_file():
                    self._text(200, target.read_text(encoding="utf-8"), "text/markdown; charset=utf-8")
                    return
                self._json(404, {"ok": False, "error": "File not found"})
                return

            if path.startswith("/materials/"):
                name = Path(parse.unquote(path.replace("/materials/", "", 1))).name
                target = MATERIAL_DIR / name
                if target.exists() and target.is_file():
                    self._bytes(200, target.read_bytes())
                    return
                self._json(404, {"ok": False, "error": "File not found"})
                return

            self._json(404, {"ok": False, "error": "Not found"})
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e), "trace": traceback.format_exc()})

    def do_POST(self):
        try:
            if self.path == "/api/login":
                data = self._read_json()
                username = str(data.get("username", "")).strip()
                password = str(data.get("password", "")).strip()

                if not AUTH_ENABLED:
                    self._json(200, {"ok": True, "token": "auth-disabled", "expiresIn": TOKEN_TTL_SECONDS})
                    return

                if username == AUTH_USERNAME and password == AUTH_PASSWORD:
                    token = secrets.token_urlsafe(32)
                    SESSIONS[token] = dt.datetime.now().timestamp() + TOKEN_TTL_SECONDS
                    self._json(200, {"ok": True, "token": token, "expiresIn": TOKEN_TTL_SECONDS})
                    return

                self._json(401, {"ok": False, "error": "用户名或密码错误"})
                return

            if self._need_auth(self.path) and not self._authorized():
                self._json(401, {"ok": False, "error": "Unauthorized"})
                return

            if self.path == "/api/upload-material":
                name = self._save_uploaded_material()
                self._json(200, {"ok": True, "file": name})
                return

            if self.path == "/api/roles/save":
                data = self._read_json()
                prompts = data.get("prompts") or {}
                if not isinstance(prompts, dict):
                    self._json(400, {"ok": False, "error": "prompts must be an object"})
                    return
                for role in ROLES:
                    v = str(prompts.get(role, "")).strip()
                    if v:
                        ROLE_PROMPTS[role] = v
                save_role_prompts(ROLE_PROMPTS)
                self._json(200, {"ok": True, "prompts": ROLE_PROMPTS})
                return

            if self.path == "/api/run-agent":
                data = self._read_json()
                role = str(data.get("role", "")).strip()
                pd = str(data.get("productDefinition", "")).strip()
                material_ids = data.get("materialIds") or []
                if not pd:
                    self._json(400, {"ok": False, "error": "productDefinition is required"})
                    return
                merged = merge_product_definition(pd, material_ids)
                filename, content = self.service.run_single(role, merged)
                self._json(200, {"ok": True, "file": filename, "url": f"/outputs/{filename}", "preview": content[:2000]})
                return

            if self.path == "/api/run-collaboration":
                data = self._read_json()
                pd = str(data.get("productDefinition", "")).strip()
                material_ids = data.get("materialIds") or []
                if not pd:
                    self._json(400, {"ok": False, "error": "productDefinition is required"})
                    return
                merged = merge_product_definition(pd, material_ids)
                filename, content = self.service.run_collaboration(merged)
                self._json(200, {"ok": True, "file": filename, "url": f"/outputs/{filename}", "preview": content[:2000]})
                return

            if self.path == "/api/test-llm":
                info = self.service.test_llm()
                self._json(200, {"ok": True, "result": info})
                return

            self._json(404, {"ok": False, "error": "Not found"})
        except error.HTTPError as e:
            self._json(502, {"ok": False, "error": f"LLM API HTTPError {e.code}"})
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e), "trace": traceback.format_exc()})


def main():
    parser = argparse.ArgumentParser(description="Multi-role agent web console")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host, use 0.0.0.0 for LAN access")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    print("=== Agent Console ===")
    print(f"URL: http://{args.host}:{args.port}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Material directory: {MATERIAL_DIR}")
    print(f"Web auth enabled: {AUTH_ENABLED}")
    if AUTH_ENABLED:
        print(f"Web username: {AUTH_USERNAME}")

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
