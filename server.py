#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import cgi
import datetime as dt
import json
import os
import re
import secrets
import subprocess
import sys
import traceback
import uuid
from html import unescape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, parse, request

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
OUTPUT_DIR = BASE_DIR / "outputs"
MATERIAL_DIR = BASE_DIR / "materials"
ROLE_PROMPTS_PATH = BASE_DIR / "role_prompts.json"
PROJECTS_DB_PATH = BASE_DIR / "projects.json"

OUTPUT_DIR.mkdir(exist_ok=True)
MATERIAL_DIR.mkdir(exist_ok=True)

ROLES = ["CTO", "PM", "SCH design", "PCB design", "test", "DFM", "Risk", "Review"]
DEFAULT_ROLE_PROMPTS = {
    "CTO": "你是 CTO。请从技术路线、系统架构、成本、里程碑与资源配置角度给出可执行建议。",
    "PM": "你是 PM（产品经理）。请从用户价值、需求边界、优先级、版本节奏、验收标准角度给出建议。",
    "SCH design": ("你是 SCH design（原理图设计）负责人。请细化关键模块和关键信号设计：电源树与时序、时钟/复位、DDR/高速接口、关键器件选型与去耦、上电时序、保护电路、测试点规划。输出中必须给出：设计约束、关键参数目标、原理图检查清单、风险与规避措施。"),
    "PCB design": ("你是 PCB design（PCB设计）负责人。请细化布局布线和关键网络规则：层叠建议、阻抗控制、差分对约束、回流路径、分区隔离、EMC/EMI、散热、DFM 规则。输出中必须给出：关键网络布线约束表、版图分区建议、SI/PI/EMI 风险与验证点。"),
    "test": "你是 test 负责人。请从测试策略、覆盖率、测试夹具、验证计划、缺陷闭环和质量门禁给出建议。",
    "DFM": "你是 DFM 负责人。请从可制造性、工艺窗口、BOM 风险、量产导入角度给出建议。",
    "Risk": "你是 Risk 负责人。请识别风险并评估概率/影响，提出缓解措施和触发条件。",
    "Review": "你是 Review 主持人。请整合各角色观点，给出冲突点、决策建议和下一步行动。",
}

AUTH_USERNAME = os.getenv("WEB_USERNAME", "admin").strip()
AUTH_PASSWORD = "admin"
AUTH_ENABLED = os.getenv("WEB_AUTH_ENABLED", "1").strip() != "0"
TOKEN_TTL_SECONDS = int(os.getenv("WEB_TOKEN_TTL_SECONDS", "43200"))
SESSIONS = {}
WEB_RESEARCH_ENABLED = os.getenv("WEB_RESEARCH_ENABLED", "1").strip() != "0"
CHINESE_OUTPUT_RULE = "所有输出必须使用简体中文，不得使用英文作为主体内容。"


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


def _load_projects_db() -> dict:
    if not PROJECTS_DB_PATH.exists():
        return {"projects": []}
    try:
        data = json.loads(PROJECTS_DB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"projects": []}
    if not isinstance(data, dict):
        return {"projects": []}
    projects = data.get("projects")
    if not isinstance(projects, list):
        return {"projects": []}
    return {"projects": projects}


def _save_projects_db(db: dict) -> None:
    PROJECTS_DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def _project_summary(project: dict) -> dict:
    return {
        "id": project.get("id", ""),
        "name": project.get("name", "Untitled"),
        "createdAt": project.get("createdAt", ""),
        "updatedAt": project.get("updatedAt", ""),
        "historyCount": len(project.get("history") or []),
        "lastFile": project.get("lastFile", ""),
    }


def list_projects() -> list:
    db = _load_projects_db()
    projects = [p for p in db.get("projects", []) if isinstance(p, dict)]
    projects.sort(key=lambda p: p.get("updatedAt", ""), reverse=True)
    return [_project_summary(p) for p in projects]


def get_project(project_id: str):
    db = _load_projects_db()
    for p in db.get("projects", []):
        if isinstance(p, dict) and p.get("id") == project_id:
            return p
    return None


def save_project(name: str, product_definition: str, project_id: str = "") -> dict:
    db = _load_projects_db()
    now = dt.datetime.now().isoformat(timespec="seconds")
    clean_name = (name or "").strip() or "Untitled Project"
    clean_pd = (product_definition or "").strip()
    projects = db.get("projects", [])

    if project_id:
        for p in projects:
            if isinstance(p, dict) and p.get("id") == project_id:
                p["name"] = clean_name
                p["productDefinition"] = clean_pd
                p["updatedAt"] = now
                _save_projects_db(db)
                return p

    new_project = {
        "id": project_id or uuid.uuid4().hex[:12],
        "name": clean_name,
        "productDefinition": clean_pd,
        "createdAt": now,
        "updatedAt": now,
        "lastFile": "",
        "history": [],
    }
    projects.append(new_project)
    db["projects"] = projects
    _save_projects_db(db)
    return new_project


def append_project_history(project_id: str, run_type: str, file_name: str, product_definition: str = "") -> None:
    if not project_id:
        return
    db = _load_projects_db()
    now = dt.datetime.now().isoformat(timespec="seconds")
    for p in db.get("projects", []):
        if isinstance(p, dict) and p.get("id") == project_id:
            history = p.get("history")
            if not isinstance(history, list):
                history = []
            history.insert(
                0,
                {
                    "time": now,
                    "type": run_type,
                    "file": file_name,
                    "url": f"/outputs/{file_name}",
                },
            )
            p["history"] = history[:100]
            p["lastFile"] = file_name
            p["updatedAt"] = now
            if product_definition.strip():
                p["productDefinition"] = product_definition.strip()
            _save_projects_db(db)
            return


def extract_pdf_text(pdf_path: Path, max_chars: int = 24000) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pypdf"],
                check=True,
                capture_output=True,
                text=True,
                timeout=90,
            )
            from pypdf import PdfReader  # type: ignore
        except Exception:
            return (
                f"[PDF 文件 {pdf_path.name} 未解析：自动安装 pypdf 失败。"
                "请手动执行 `python -m pip install pypdf` 后重试。]"
            )

    try:
        reader = PdfReader(str(pdf_path))
        texts = []
        for page in reader.pages:
            texts.append(page.extract_text() or "")
        merged = "\n".join(texts).strip()
        if not merged:
            return f"[PDF 文件 {pdf_path.name} 已读取，但未提取到文本（可能是扫描版）。]"
        return merged[:max_chars]
    except Exception as e:
        return f"[PDF 文件 {pdf_path.name} 解析失败: {e}]"


def _duckduckgo_search(query: str, max_items: int = 5) -> list:
    search_url = "https://html.duckduckgo.com/html/?q=" + parse.quote(query)
    req = request.Request(
        search_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
            )
        },
    )
    with request.urlopen(req, timeout=12) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    links = re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S)
    snippets = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', html, flags=re.I | re.S)

    out = []
    for i, (href, title_html) in enumerate(links[:max_items]):
        title = re.sub(r"<[^>]+>", "", title_html)
        title = unescape(title).strip()
        snippet = ""
        if i < len(snippets):
            snippet = re.sub(r"<[^>]+>", "", snippets[i])
            snippet = unescape(snippet).strip()
        out.append({"title": title, "url": unescape(href), "snippet": snippet})
    return out


def build_web_research_context(product_definition: str) -> str:
    if not WEB_RESEARCH_ENABLED:
        return "[联网检索已关闭]"

    # 只用前 120 字构建查询，避免过长查询导致失败
    query_seed = re.sub(r"\s+", " ", product_definition.strip())[:120]
    query = f"{query_seed} datasheet 设计 要点"
    try:
        items = _duckduckgo_search(query, max_items=5)
    except Exception as e:
        return f"[联网检索失败: {e}]"

    if not items:
        return "[联网检索无结果]"

    lines = ["## 联网检索补充（自动）", f"- 查询词: {query}", ""]
    for idx, it in enumerate(items, start=1):
        lines.append(f"### 结果 {idx}")
        lines.append(f"- 标题: {it['title']}")
        lines.append(f"- 链接: {it['url']}")
        if it["snippet"]:
            lines.append(f"- 摘要: {it['snippet'][:220]}")
        lines.append("")
    return "\n".join(lines).strip()


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
    if target.suffix.lower() == ".pdf":
        return extract_pdf_text(target)

    text_ext = {".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".log", ".py", ".js", ".ts", ".html", ".css"}
    if target.suffix.lower() not in text_ext:
        return f"[文件 {target.name} 为非文本格式，当前仅展示文件名]"
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = target.read_text(encoding="gbk", errors="ignore")
    return content[:12000]


def merge_product_definition(product_definition: str, material_ids) -> str:
    base = product_definition.strip()
    material_ids = material_ids or []
    sections = [base]

    web_context = build_web_research_context(base)
    if web_context:
        sections.extend(["\n\n---\n\n", web_context, "\n"])

    if not material_ids:
        return "".join(sections).strip()

    sections.extend(["\n\n---\n\n## 参考资料\n"])
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
        system_prompt = f"{system_prompt}\n\n{CHINESE_OUTPUT_RULE}"
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
                "- 输出策略: 先给结论，再给依据，再给行动项。",
                "- 约束策略: 对未知参数列出确认清单与临时设计假设。",
                "",
                "## 建议行动",
                "1. 补齐关键 Datasheet 参数与约束。",
                "2. 按模块建立设计检查清单与验证计划。",
                "3. 每轮评审输出风险闭环与责任人。",
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

    def _role_focus(self, role: str) -> str:
        if role == "SCH design":
            return (
                "必须细化：关键器件选型依据、供电/时钟/复位方案、关键接口引脚分配、"
                "关键模块（电源、主控、存储、外设）连接细节、关键信号完整性约束。"
            )
        if role == "PCB design":
            return (
                "必须细化：层叠与阻抗规划、关键网络（时钟/DDR/高速差分/电源）约束、"
                "回流路径、EMI 控制、热设计、可制造性规则。"
            )
        return "请基于资料给出可执行、可验证的工程结论。"

    def run_single(self, role: str, product_definition: str):
        if role not in ROLES:
            raise ValueError(f"Unknown role: {role}")
        system = ROLE_PROMPTS[role] + "\n" + CHINESE_OUTPUT_RULE
        user = (
            "请基于以下输入输出 Markdown 报告，章节至少包括：结论摘要、关键问题、设计细节、建议、下一步行动。\n"
            f"附加要求：{self._role_focus(role)}\n"
            "禁止仅以“Datasheet 参数未知”结束，必须给出：需要确认的参数清单 + 当前可行的临时设计假设。\n\n"
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
                "你将参与跨职能评审。先独立给出观点。输出 markdown，包含：立场、发现、设计细节、建议、阻塞项。\n"
                f"附加要求：{self._role_focus(role)}\n"
                "禁止仅写“Datasheet 参数未知”，请给出需确认参数清单与临时假设。\n\n"
                f"产品定义:\n{product_definition.strip()}"
            )
            initial[role] = self.llm.generate(ROLE_PROMPTS[role] + "\n" + CHINESE_OUTPUT_RULE, prompt)
        rounds.append(("Round 1", initial))

        discussion = {}
        digest = "\n\n".join([f"### {r}\n{initial[r][:2500]}" for r in ROLES])
        for role in ROLES:
            prompt = (
                "请基于其他角色观点进行回应与协同，输出 markdown，包含：认同点、分歧点、需验证假设、行动项。\n"
                f"附加要求：{self._role_focus(role)}\n\n"
                f"产品定义:\n{product_definition.strip()}\n\n"
                f"跨角色观点摘要:\n{digest}"
            )
            discussion[role] = self.llm.generate(ROLE_PROMPTS[role] + "\n" + CHINESE_OUTPUT_RULE, prompt)
        rounds.append(("Round 2", discussion))

        round_summaries = []
        for label, data in rounds:
            round_input = "\n\n".join([f"## {role}\n{data[role][:2200]}" for role in ROLES])
            summary = self.llm.generate(
                ROLE_PROMPTS["Review"] + "\n" + CHINESE_OUTPUT_RULE,
                "请基于本轮各角色发言输出本轮总结（markdown），包含："
                "本轮结论、主要共识、关键分歧、待验证项、下一步行动（最多5条）。\n\n"
                f"本轮记录:\n{round_input}",
            )
            round_summaries.append((label, summary))

        synthesis_input = "\n\n".join(
            [f"## {label} - {role}\n{content[:3000]}" for label, data in rounds for role, content in data.items()]
        )
        final = self.llm.generate(
            ROLE_PROMPTS["Review"] + "\n" + CHINESE_OUTPUT_RULE,
            "请输出最终联合结论（markdown），包含：最终决策、风险闭环、里程碑、责任分配（RACI）、本周行动清单。\n"
            "输出必须为中文。\n\n"
            f"产品定义:\n{product_definition.strip()}\n\n"
            f"讨论记录:\n{synthesis_input}",
        )

        out = [
            "# 多角色协作报告",
            "",
            f"- 时间: {dt.datetime.now().isoformat(timespec='seconds')}",
            "",
            "## 1. 结论",
            "",
            final,
            "",
            "## 2. 产品定义",
            "```text",
            product_definition.strip(),
            "```",
            "",
        ]

        for idx, (label, data) in enumerate(rounds, start=1):
            out.append(f"## {idx + 2}. {label}")
            out.append("")
            out.append("### 本轮总结")
            out.append("")
            out.append(round_summaries[idx - 1][1])
            out.append("")
            for role in ROLES:
                out.append(f"### {role}")
                out.append("")
                out.append(data[role])
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
        if path in ["/", "/index.html", "/api/login", "/api/health"]:
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

            if path == "/api/projects":
                self._json(200, {"ok": True, "projects": list_projects()})
                return

            if path.startswith("/api/projects/"):
                project_id = path.replace("/api/projects/", "", 1).strip()
                project = get_project(project_id)
                if not project:
                    self._json(404, {"ok": False, "error": "Project not found"})
                    return
                self._json(200, {"ok": True, "project": project})
                return

            if path == "/api/auth-info":
                self._json(200, {"ok": True, "authEnabled": AUTH_ENABLED})
                return

            if path == "/api/health":
                self._json(200, {"ok": True, "status": "healthy"})
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

                self._json(401, {"ok": False, "error": "鐢ㄦ埛鍚嶆垨瀵嗙爜閿欒"})
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

            if self.path == "/api/projects/save":
                data = self._read_json()
                project_id = str(data.get("id", "")).strip()
                name = str(data.get("name", "")).strip()
                pd = str(data.get("productDefinition", "")).strip()
                project = save_project(name, pd, project_id=project_id)
                self._json(200, {"ok": True, "project": project, "summary": _project_summary(project)})
                return

            if self.path == "/api/run-agent":
                data = self._read_json()
                role = str(data.get("role", "")).strip()
                pd = str(data.get("productDefinition", "")).strip()
                project_id = str(data.get("projectId", "")).strip()
                material_ids = data.get("materialIds") or []
                if not pd:
                    self._json(400, {"ok": False, "error": "productDefinition is required"})
                    return
                merged = merge_product_definition(pd, material_ids)
                filename, content = self.service.run_single(role, merged)
                append_project_history(project_id, "single", filename, pd)
                self._json(200, {"ok": True, "file": filename, "url": f"/outputs/{filename}", "preview": content[:2000]})
                return

            if self.path == "/api/run-collaboration":
                data = self._read_json()
                pd = str(data.get("productDefinition", "")).strip()
                project_id = str(data.get("projectId", "")).strip()
                material_ids = data.get("materialIds") or []
                if not pd:
                    self._json(400, {"ok": False, "error": "productDefinition is required"})
                    return
                merged = merge_product_definition(pd, material_ids)
                filename, content = self.service.run_collaboration(merged)
                append_project_history(project_id, "collaboration", filename, pd)
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
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="Bind host, use 0.0.0.0 for LAN access")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8787")))
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


