"""SB.1 — Tiered permission gate: tool call classification.

Every tool call passes through classify_tool() before execution.
The result determines what happens next:

  Tier.ZERO  → Hard-reject. No approval path. Ever.
  Tier.ONE   → Requires approval (session pre-approval or admin channel YES in SB.2).
  Tier.TWO   → Always free. No approval needed.

Governing principle: Trust the environment, not the text.
Text-based patterns are defense-in-depth, not the primary defense.
The real safety boundary is which environment a command runs in:
  Docker container (ephemeral, non-root, resource-limited) → Tier 2 always
  Host shell (root, permanent, real filesystem)            → Tier 1 unless clearly safe

See SECURITY.md for the full tier specification and rationale.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Tier(Enum):
    """Tool execution permission tier."""

    ZERO = 0  # Absolutely forbidden — no approval path
    ONE = 1   # Requires explicit approval
    TWO = 2   # Always free


@dataclass
class GateDecision:
    """Result of a gate classification check."""

    tier: Tier
    reason: str
    category: str = field(default="")  # pre-approval category key (Tier 1 only)


# ---------------------------------------------------------------------------
# Exec command classification
# ---------------------------------------------------------------------------

# Tier 0: hard-reject patterns. No approval path. Matched on lowercased command.
_TIER0_EXEC: list[tuple[str, str]] = [
    # Recursive deletes (rm -r, rm -rf, rm -fr, rm -R, rm --recursive)
    (r"\brm\s+(-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)\b", "recursive delete (rm -r/-rf/-fr)"),
    # find with destructive actions
    (r"\bfind\b.+(-delete\b|-exec\s+rm\b)", "find -delete or find -exec rm"),
    # Disk destruction
    (r"\bdd\s+if=", "disk overwrite (dd if=)"),
    (r"\b(mkfs|wipefs)\b", "disk destruction (mkfs/wipefs)"),
    (r"\bfdisk\b", "disk partitioning (fdisk)"),
    # System power
    (r"\b(shutdown|reboot|poweroff|halt)\b", "system shutdown/reboot"),
    # Recursive chmod and chmod 777
    (r"\bchmod\s+(-[Rr]\b|--recursive\b)", "recursive chmod"),
    (r"\bchmod\s+777\b", "chmod 777"),
    # Fork bomb
    (r":\(\)\s*\{.*\};\s*:", "fork bomb"),
]

# Tier 0: rm targeting protected system or config paths (even without -r flag)
_PROTECTED_PATHS_RE = re.compile(
    r"\brm\b.+(/etc/|/usr/|/bin/|/sbin/|/lib/|/boot/|\.hive/logs/|\.hive/config\.json)"
)

# Pipe-to-interpreter check: Tier 1 regardless of allowlist (bypass prevention).
# Must be checked BEFORE the workspace-constrained and text allowlists.
_PIPE_INTERPRETER_RE = re.compile(
    r"\|\s*(bash|sh|zsh|fish|dash|python3?|node|nodejs|ruby|perl)\b"
)

# Workspace-constrained exclusions: operations that remain Tier 1 even when
# run from within the workspace directory. These have effects outside the
# workspace (process management, remote state, host packages) or are
# irreversible within it (rm).
_WORKSPACE_EXCLUDED_RE = re.compile(
    r"\brm\b"
    r"|\b(kill|pkill|killall)\b"
    r"|\bsystemctl\b"
    r"|\bpip\s+(install|uninstall)\b"
    r"|\bapt(-get)?\s+(install|remove|purge)\b"
    r"|\bdpkg\b"
    r"|\bgit\s+(push|reset)\b"
    r"|\bgit\s+checkout\s+--"
)

# Tier 2: read-only text allowlist. Matches commands that clearly cannot
# modify system state regardless of working directory. Checked after the
# workspace-constrained check.
_TIER2_EXEC: list[str] = [
    r"\b(ls|ll|la)\b",
    r"\bps\b",
    r"\b(df|du)\b",
    r"\b(cat|tail|less|more)\b",
    r"\bhead\b(?![~^])",    # head command, but not HEAD~N / HEAD^ git refs
    r"\b(grep|rg|ripgrep|awk|sed)\b",
    r"\bfind\b",            # safe: Tier 0 -delete/-exec rm already rejected above
    r"\bgit\s+(status|log|diff|show|branch|remote|fetch)\b",
    r"\bgit\s+stash\s+(list|show)\b",
    r"\b(top|htop)\b",
    r"\b(free|uptime|uname|whoami|who|id|hostname)\b",
    r"\b(which|type|whereis|env|printenv)\b",
    r"\b(stat|wc|sort|uniq|cut|tr)\b",
    r"\becho\b",
    r"\bpwd\b",
    r"\bdate\b",
    r"\bdocker\s+(ps|images|stats|logs|inspect)\b",
    r"\bpip\s+(list|show|freeze|check)\b",
    r"\bnpm\s+(list|ls|audit)\b",
    r"\b(curl|wget)\b",     # HTTP fetches — content audited separately
    r"\bjq\b",
]

# Tier 1: dangerous-but-approvable patterns.
_TIER1_EXEC: list[tuple[str, str, str]] = [
    # (pattern, reason, category)
    (r"\brm\b", "file delete", "exec"),
    (r"\b(kill|pkill|killall)\b", "process termination", "exec"),
    (r"\bmv\b", "file move (may overwrite)", "exec"),
    (r"\bcp\s+(-[a-zA-Z]*f|--force)\b", "force-copy (may overwrite)", "exec"),
    (r"\btruncate\b", "file truncation", "exec"),
    (r"\b(chmod|chown)\b", "permission/ownership change", "exec"),
    (r"\bsystemctl\s+(start|stop|restart|enable|disable)\b", "service management", "exec"),
    (r"\bcrontab\b|\bcron\s+add\b", "cron registration", "exec"),
    (r"\bpip\s+(install|uninstall)\b", "host-level pip (use docker_exec for isolation)", "packages"),
    (r"\bapt(-get)?\s+(install|remove|purge)\b|\bdpkg\b", "system package management", "packages"),
    (r"\bgit\s+push\b", "git push (remote state change)", "git"),
    (r"\bgit\s+reset\b", "git reset", "git"),
    (r"\bgit\s+checkout\s+--", "git checkout -- (destructive local reset)", "git"),
    # Running script files on the host
    (r"\b(python3?|bash|sh|zsh|fish|node|nodejs)\s+\S+\.(py|sh|bash|zsh|js)\b", "running a script file", "exec"),
    (r"\./[^\s|;&]+\.(sh|bash|zsh|py|js)\b", "running a script file", "exec"),
    (r"\bpython3?\s+-c\b", "inline python execution (use docker_exec for isolation)", "exec"),
]


def classify_exec(
    command: str,
    workspace: Path | None = None,
    working_dir: str | None = None,
) -> GateDecision:
    """Classify a shell command string into a permission tier.

    Checks in order:
      1. Tier 0 hard-reject patterns
      2. Tier 0 protected system paths (rm on /etc, /usr, etc.)
      3. Pipe-to-interpreter → Tier 1 (bypass prevention)
      4. Workspace-constrained exec → Tier 2 (environment allowlist)
      5. Tier 2 read-only text allowlist
      6. Tier 1 specific dangerous patterns
      7. Default: Tier 1 (safe default for unknown commands)

    Args:
        command:     The shell command to classify.
        workspace:   The hive workspace directory (for workspace-constrained check).
        working_dir: The command's working directory (from exec params).

    Returns:
        GateDecision with the applicable tier, reason, and pre-approval category.
    """
    lower = command.strip().lower()

    # 1. Tier 0: absolute hard-reject patterns
    for pattern, reason in _TIER0_EXEC:
        if re.search(pattern, lower):
            return GateDecision(Tier.ZERO, f"Forbidden: {reason}")

    # 2. Tier 0: rm targeting protected system/config paths
    if _PROTECTED_PATHS_RE.search(lower):
        return GateDecision(Tier.ZERO, "Forbidden: rm on protected system path")

    # 3. Pipe-to-interpreter → Tier 1 (must precede allowlists)
    if _PIPE_INTERPRETER_RE.search(lower):
        return GateDecision(Tier.ONE, "Requires approval: pipe to shell interpreter", "exec")

    # 4. Workspace-constrained exec → Tier 2
    if workspace and working_dir and _workspace_constrained(command, lower, workspace, working_dir):
        # SB.4: Skill First-Run Gate
        patterns = [
            r"\b(?:python3?|bash|sh|zsh|fish|node|nodejs)\s+(\S+\.(?:py|sh|bash|zsh|js))\b",
            r"(\./[^\s|;&]+\.(?:sh|bash|zsh|py|js))\b"
        ]
        
        for pat in patterns:
            for match in re.finditer(pat, command):
                script_pth = match.group(1)
                try:
                    cwd_path = Path(working_dir).expanduser().resolve()
                    resolved_script = (cwd_path / script_pth).resolve()
                    if resolved_script.is_file():
                        import hashlib
                        import json
                        content = resolved_script.read_bytes()
                        script_hash = hashlib.sha256(content).hexdigest()
                        
                        system_dir = workspace / ".system"
                        approved_json_path = system_dir / "approved_scripts.json"
                        approved = False
                        if approved_json_path.exists():
                            try:
                                approved_data = json.loads(approved_json_path.read_text())
                                if script_hash in approved_data.get("approved_hashes", []):
                                    approved = True
                            except Exception:
                                pass
                        if not approved:
                            return GateDecision(
                                Tier.ONE,
                                f"First-run approval required for script: {script_pth} (hash: {script_hash[:8]}). Please review the script's contents.",
                                f"script_approval:{script_hash}:{str(resolved_script)}"
                            )
                except Exception:
                    continue
                    
        return GateDecision(Tier.TWO, "workspace-constrained exec")

    # 5. Tier 2: read-only text allowlist
    for pattern in _TIER2_EXEC:
        if re.search(pattern, lower):
            return GateDecision(Tier.TWO, "read-only command")

    # 6. Tier 1: specific dangerous-but-approvable patterns
    for pattern, reason, category in _TIER1_EXEC:
        if re.search(pattern, lower):
            return GateDecision(Tier.ONE, f"Requires approval: {reason}", category)

    # 7. Default: unknown commands are Tier 1 (safe default)
    return GateDecision(Tier.ONE, "Requires approval: unknown command (safe default)", "exec")


# ---------------------------------------------------------------------------
# Tool call classification
# ---------------------------------------------------------------------------


def classify_tool(
    name: str,
    params: dict[str, Any],
    workspace: Path | None = None,
) -> GateDecision:
    """Classify a tool call into a permission tier.

    Args:
        name:      Registered tool name (e.g. "exec", "write_file").
        params:    Tool call parameters as passed to ToolRegistry.execute().
        workspace: Resolved workspace path. Write/edit within workspace is Tier 2.

    Returns:
        GateDecision with the applicable tier, reason, and pre-approval category.
    """
    # exec: tier depends on command string + working directory
    if name == "exec":
        return classify_exec(
            params.get("command", ""),
            workspace=workspace,
            working_dir=params.get("working_dir"),
        )

    # docker_exec: always Tier 2 — ephemeral container IS the approval mechanism
    if name == "docker_exec":
        return GateDecision(Tier.TWO, "Docker sandbox is the security boundary")

    # Always-free tools (including session_approve itself — gating it would be recursive)
    if name in {
        "read_file", "list_dir", "web_search", "web_fetch",
        "message", "report_task", "session_approve",
        "spawn", "spawn_pipeline", "workers"
    }:
        return GateDecision(Tier.TWO, "always free")

    # write_file: workspace (≤ 10 KB) → Tier 2, outside or large overwrite → Tier 1
    if name == "write_file":
        path = params.get("path", "")
        if workspace and _within_workspace(path, workspace):
            try:
                resolved = Path(path).expanduser().resolve()
                if resolved.exists() and resolved.stat().st_size > 10_240:
                    return GateDecision(
                        Tier.ONE,
                        f"overwriting file larger than 10 KB: {path!r}",
                        "write",
                    )
            except OSError:
                pass
            return GateDecision(Tier.TWO, "write_file within workspace")
        return GateDecision(Tier.ONE, f"write_file outside workspace: {path!r}", "write")

    # edit_file: workspace → Tier 2, outside → Tier 1
    if name == "edit_file":
        path = params.get("path", "")
        if workspace and _within_workspace(path, workspace):
            return GateDecision(Tier.TWO, "edit_file within workspace")
        return GateDecision(Tier.ONE, f"edit_file outside workspace: {path!r}", "write")

    # cron: always Tier 1
    if name == "cron":
        return GateDecision(Tier.ONE, "cron job registration", "exec")

    # Unknown tool: Tier 1 by default (safe default)
    return GateDecision(Tier.ONE, f"unknown tool {name!r} (default: requires approval)", "exec")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _within_workspace(path: str, workspace: Path) -> bool:
    """Return True if path resolves to within the workspace directory."""
    try:
        resolved = Path(path).expanduser().resolve()
        ws = workspace.resolve()
        return resolved == ws or ws in resolved.parents
    except (ValueError, OSError):
        return False


def _workspace_constrained(
    command: str,
    lower: str,
    workspace: Path,
    working_dir: str,
) -> bool:
    """Return True if the exec command is safely constrained to the workspace.

    Conditions (ALL must hold):
    - working_dir resolves to inside the workspace directory
    - command has no path traversal (../ or ..\\)
    - command has no sudo
    - command does not match workspace-excluded patterns (rm, kill, systemctl,
      pip install, apt, git push/reset — operations with host-level effects)
    """
    try:
        resolved_wd = Path(working_dir).expanduser().resolve()
        ws = workspace.resolve()
        if resolved_wd != ws and ws not in resolved_wd.parents:
            return False
    except (ValueError, OSError):
        return False

    if "../" in command or "..\\" in command:
        return False

    if "sudo" in lower:
        return False

    if _WORKSPACE_EXCLUDED_RE.search(lower):
        return False

    return True