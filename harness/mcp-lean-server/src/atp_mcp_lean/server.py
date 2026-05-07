"""MCP server entrypoint: stdio transport, tools backed by repl_session.

Tools exposed:
  - repl_open(problem_id)
  - repl_step(session_id, tactic)
  - repl_close(session_id)
  - loogle(query)
  - exact_q(session_id)
  - apply_q(session_id)
  - mathlib_find(pattern)
  - lean_check(file_relpath, source)
  - mathlib_search(query)         [explicit fallback; ripgrep over mathlib]

Fail fast on tooling problems — no silent fallbacks except the documented
mathlib_search fallback the agent must opt into by name.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .repl_session import LEAN_PROJECT, ReplPool


_pool = ReplPool()


def _mathlib_dir() -> Path:
    p = LEAN_PROJECT / ".lake" / "packages" / "mathlib" / "Mathlib"
    if not p.exists():
        raise RuntimeError(
            f"mathlib not found at {p}; ran `harness/setup.sh`?"
        )
    return p


def _ripgrep(pattern: str, max_results: int = 30) -> list[dict]:
    if shutil.which("rg") is None:
        raise RuntimeError("ripgrep (rg) is required for mathlib_search")
    proc = subprocess.run(
        [
            "rg", "--no-heading", "--line-number", "--max-count", str(max_results),
            "--max-columns", "240", pattern, str(_mathlib_dir()),
        ],
        capture_output=True, text=True, timeout=20,
    )
    out: list[dict] = []
    for line in proc.stdout.splitlines()[:max_results]:
        parts = line.split(":", 2)
        if len(parts) == 3:
            out.append({"file": parts[0], "line": int(parts[1]), "text": parts[2]})
    return out


def build_server() -> Server:
    server: Server = Server("atp-mcp-lean")

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [
            Tool(
                name="repl_open",
                description=(
                    "Open a fresh Lean REPL session for a registered problem ID "
                    "(e.g. 'putnam_2022_a3'). Returns {session_id, theorem_name, "
                    "initial_goal}. Mathlib is preloaded."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "problem_id": {"type": "string"},
                    },
                    "required": ["problem_id"],
                },
            ),
            Tool(
                name="repl_step",
                description=(
                    "Apply one tactic to the open proof state in the session. "
                    "Returns the new goals (or {closed: true}) and any messages."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "tactic": {"type": "string"},
                    },
                    "required": ["session_id", "tactic"],
                },
            ),
            Tool(
                name="repl_close",
                description="Release a session.",
                inputSchema={
                    "type": "object",
                    "properties": {"session_id": {"type": "string"}},
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="loogle",
                description=(
                    "Query loogle for mathlib lemmas matching a pattern. "
                    "Example pattern: 'List.length, _ + _ = _' or 'Nat.add_comm'."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            ),
            Tool(
                name="exact_q",
                description=(
                    "Drive `exact?` against the session's current goal; returns "
                    "Lean's suggested closing terms (if any)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {"session_id": {"type": "string"}},
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="apply_q",
                description=(
                    "Drive `apply?` against the session's current goal; returns "
                    "Lean's suggested matching lemmas."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {"session_id": {"type": "string"}},
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="mathlib_find",
                description="Run `#find` (Mathlib.Tactic.Find) with a syntactic pattern.",
                inputSchema={
                    "type": "object",
                    "properties": {"pattern": {"type": "string"}},
                    "required": ["pattern"],
                },
            ),
            Tool(
                name="lean_check",
                description=(
                    "Compile a Lean file (relative path under sandbox dir; the "
                    "harness's `lake env lean` is used). Returns {success, "
                    "exit_code, stdout, stderr}. This is the official grader."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_relpath": {"type": "string"},
                        "source": {"type": "string"},
                    },
                    "required": ["file_relpath", "source"],
                },
            ),
            Tool(
                name="mathlib_search",
                description=(
                    "FALLBACK: ripgrep over Mathlib/. Use only when semantic "
                    "tools (loogle/exact?/apply?/find) failed."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "default": 20},
                    },
                    "required": ["query"],
                },
            ),
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name == "repl_open":
                s = _pool.open(arguments["problem_id"])
                payload = {
                    "session_id": s.session_id,
                    "problem_id": s.problem_id,
                    "theorem_name": s.theorem_name,
                    "initial_goal": s.initial_goal,
                }
            elif name == "repl_step":
                payload = _pool.step(arguments["session_id"], arguments["tactic"])
            elif name == "repl_close":
                _pool.close(arguments["session_id"])
                payload = {"closed": True}
            elif name == "loogle":
                payload = _pool.loogle(arguments["query"])
            elif name == "exact_q":
                payload = _pool.exact_q(arguments["session_id"])
            elif name == "apply_q":
                payload = _pool.apply_q(arguments["session_id"])
            elif name == "mathlib_find":
                payload = _pool.find(arguments["pattern"])
            elif name == "lean_check":
                payload = _pool.lean_check(
                    arguments["file_relpath"], arguments["source"]
                )
            elif name == "mathlib_search":
                hits = _ripgrep(
                    arguments["query"], int(arguments.get("max_results", 20))
                )
                payload = {"hits": hits}
            else:
                raise ValueError(f"Unknown tool: {name}")
        except Exception as exc:  # noqa: BLE001 — surface every error verbatim
            payload = {"error": f"{type(exc).__name__}: {exc}"}
        return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]

    return server


def main() -> None:
    async def _run() -> None:
        async with stdio_server() as (read, write):
            await build_server().run(read, write, build_server().create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
