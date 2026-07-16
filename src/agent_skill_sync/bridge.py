from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BridgeStatus:
    codex_calls_claude: bool
    claude_calls_codex: bool
    detail: str


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    preferred_bins = {
        str(path.parent)
        for executable in ("codex", "claude")
        if (path := Path(shutil.which(executable) or "")).name
    }
    env["PATH"] = os.pathsep.join([*sorted(preferred_bins), env.get("PATH", "")])
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
        env=env,
    )


def status() -> BridgeStatus:
    codex = _run(["codex", "mcp", "list"])
    claude = _run(["claude", "mcp", "get", "codex"])
    codex_calls_claude = "claude-code" in codex.stdout and "enabled" in codex.stdout
    claude_calls_codex = claude.returncode == 0
    detail = "\n".join(part.strip() for part in (codex.stdout, codex.stderr, claude.stdout, claude.stderr) if part.strip())
    return BridgeStatus(codex_calls_claude, claude_calls_codex, detail)


def configure(direction: str) -> subprocess.CompletedProcess[str]:
    wrapper = shutil.which("mcp-bridge")
    if wrapper:
        mapping = {
            "codex-calls-claude": "claude-in-codex",
            "claude-calls-codex": "codex-in-claude",
            "both": "both",
        }
        return _run([wrapper, mapping[direction]])
    if direction == "codex-calls-claude":
        return _run(["codex", "mcp", "add", "claude-code", "--", "claude", "mcp", "serve"])
    if direction == "claude-calls-codex":
        return _run(["claude", "mcp", "add", "codex", "--", "codex", "mcp-server"])
    raise RuntimeError("Configuring both directions requires the mcp-bridge wrapper")
