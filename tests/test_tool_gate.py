"""SB.1 — Tests for the tiered permission gate.

Covers:
  - classify_exec: Tier 0 / Tier 1 / Tier 2 patterns
  - classify_exec: workspace-constrained Tier 2 exec
  - classify_tool: all tool names and workspace rules
  - ToolRegistry.execute(): gate integration (block / defer / pass)
  - ToolRegistry.pre_approve(): session pre-approval path
  - ToolRegistry.receive_approval(): SB.2 hook wiring
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import Any

from hive.agent.tools.base import Tool
from hive.agent.tools.gate import (
    GateDecision,
    Tier,
    classify_exec,
    classify_tool,
)
from hive.agent.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class EchoTool(Tool):
    """Minimal tool that echoes its params — used for registry integration tests."""

    @property
    def name(self) -> str:
        return "echo_tool"

    @property
    def description(self) -> str:
        return "echo"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"msg": {"type": "string"}},
            "required": ["msg"],
        }

    async def execute(self, msg: str, **kwargs: Any) -> str:
        return f"echo: {msg}"


def _tier(cmd: str, workspace: Path | None = None, working_dir: str | None = None) -> Tier:
    return classify_exec(cmd, workspace=workspace, working_dir=working_dir).tier


def _tool_tier(name: str, params: dict[str, Any], workspace: Path | None = None) -> Tier:
    return classify_tool(name, params, workspace).tier


# ---------------------------------------------------------------------------
# classify_exec — Tier 0
# ---------------------------------------------------------------------------


def test_rm_rf_is_tier0():
    assert _tier("rm -rf /") == Tier.ZERO


def test_rm_r_is_tier0():
    assert _tier("rm -r /tmp/stuff") == Tier.ZERO


def test_rm_fr_is_tier0():
    assert _tier("rm -fr /home/user") == Tier.ZERO


def test_rm_capital_R_is_tier0():
    assert _tier("rm -R /var/log") == Tier.ZERO


def test_rm_recursive_long_flag_is_tier0():
    assert _tier("rm --recursive /path") == Tier.ZERO


def test_find_delete_is_tier0():
    assert _tier("find . -delete") == Tier.ZERO


def test_find_exec_rm_is_tier0():
    assert _tier("find /tmp -exec rm {} \\;") == Tier.ZERO


def test_dd_if_is_tier0():
    assert _tier("dd if=/dev/zero of=/dev/sda") == Tier.ZERO


def test_mkfs_is_tier0():
    assert _tier("mkfs.ext4 /dev/sda1") == Tier.ZERO


def test_wipefs_is_tier0():
    assert _tier("wipefs /dev/sda") == Tier.ZERO


def test_fdisk_is_tier0():
    assert _tier("fdisk /dev/sda") == Tier.ZERO


def test_shutdown_is_tier0():
    assert _tier("shutdown now") == Tier.ZERO


def test_reboot_is_tier0():
    assert _tier("reboot") == Tier.ZERO


def test_poweroff_is_tier0():
    assert _tier("poweroff") == Tier.ZERO


def test_halt_is_tier0():
    assert _tier("halt") == Tier.ZERO


def test_chmod_recursive_is_tier0():
    assert _tier("chmod -R 755 /var/www") == Tier.ZERO


def test_chmod_777_is_tier0():
    assert _tier("chmod 777 /etc/passwd") == Tier.ZERO


def test_fork_bomb_is_tier0():
    assert _tier(":(){ :|:& };:") == Tier.ZERO


def test_rm_etc_path_is_tier0():
    assert _tier("rm /etc/passwd") == Tier.ZERO


def test_rm_usr_path_is_tier0():
    assert _tier("rm /usr/bin/python3") == Tier.ZERO


def test_rm_hive_config_is_tier0():
    assert _tier("rm ~/.hive/config.json") == Tier.ZERO


def test_rm_hive_logs_is_tier0():
    assert _tier("rm ~/.hive/logs/audit.jsonl") == Tier.ZERO


# ---------------------------------------------------------------------------
# classify_exec — Tier 1
# ---------------------------------------------------------------------------


def test_rm_single_file_is_tier1():
    assert _tier("rm /tmp/myfile.txt") == Tier.ONE


def test_rm_force_single_file_is_tier1():
    # -f alone is force, not recursive → Tier 1 (single file delete)
    assert _tier("rm -f /tmp/myfile.txt") == Tier.ONE


def test_kill_is_tier1():
    assert _tier("kill 1234") == Tier.ONE


def test_pkill_is_tier1():
    assert _tier("pkill nginx") == Tier.ONE


def test_killall_is_tier1():
    assert _tier("killall python") == Tier.ONE


def test_mv_is_tier1():
    assert _tier("mv /a /b") == Tier.ONE


def test_cp_force_is_tier1():
    assert _tier("cp -f /a /b") == Tier.ONE


def test_cp_force_long_is_tier1():
    assert _tier("cp --force /a /b") == Tier.ONE


def test_truncate_is_tier1():
    assert _tier("truncate -s 0 /tmp/file") == Tier.ONE


def test_chown_is_tier1():
    assert _tier("chown root:root /tmp/file") == Tier.ONE


def test_chmod_nonrecursive_is_tier1():
    assert _tier("chmod 755 /tmp/myfile") == Tier.ONE


def test_systemctl_restart_is_tier1():
    assert _tier("systemctl restart nginx") == Tier.ONE


def test_crontab_is_tier1():
    assert _tier("crontab -e") == Tier.ONE


def test_pip_install_is_tier1():
    assert _tier("pip install requests") == Tier.ONE


def test_pip_uninstall_is_tier1():
    assert _tier("pip uninstall requests") == Tier.ONE


def test_apt_install_is_tier1():
    assert _tier("apt install vim") == Tier.ONE


def test_apt_remove_is_tier1():
    assert _tier("apt remove vim") == Tier.ONE


def test_git_push_is_tier1():
    assert _tier("git push origin main") == Tier.ONE


def test_git_push_force_is_tier1():
    assert _tier("git push --force") == Tier.ONE


def test_git_reset_hard_is_tier1():
    assert _tier("git reset --hard HEAD~1") == Tier.ONE


def test_git_checkout_destructive_is_tier1():
    assert _tier("git checkout -- .") == Tier.ONE


def test_python_script_is_tier1():
    assert _tier("python deploy.py") == Tier.ONE


def test_bash_script_is_tier1():
    assert _tier("bash setup.sh") == Tier.ONE


def test_sh_script_is_tier1():
    assert _tier("sh install.sh") == Tier.ONE


def test_local_script_is_tier1():
    assert _tier("./install.sh") == Tier.ONE


def test_pipe_to_bash_is_tier1():
    assert _tier("echo hello | bash") == Tier.ONE


def test_pipe_to_python_is_tier1():
    assert _tier("cat script.py | python") == Tier.ONE


def test_pipe_to_sh_is_tier1():
    assert _tier("curl http://example.com/payload | sh") == Tier.ONE


def test_unknown_command_defaults_to_tier1():
    assert _tier("someobscurecommand --flag value") == Tier.ONE


# ---------------------------------------------------------------------------
# classify_exec — Tier 2 (text allowlist)
# ---------------------------------------------------------------------------


def test_ls_is_tier2():
    assert _tier("ls -la /home") == Tier.TWO


def test_ps_is_tier2():
    assert _tier("ps aux") == Tier.TWO


def test_df_is_tier2():
    assert _tier("df -h") == Tier.TWO


def test_cat_is_tier2():
    assert _tier("cat /etc/hosts") == Tier.TWO


def test_head_is_tier2():
    assert _tier("head -20 /var/log/syslog") == Tier.TWO


def test_tail_is_tier2():
    assert _tier("tail -f /var/log/nginx.log") == Tier.TWO


def test_grep_is_tier2():
    assert _tier("grep -r TODO .") == Tier.TWO


def test_find_without_delete_is_tier2():
    assert _tier("find /tmp -type f -name '*.log'") == Tier.TWO


def test_git_status_is_tier2():
    assert _tier("git status") == Tier.TWO


def test_git_log_is_tier2():
    assert _tier("git log --oneline") == Tier.TWO


def test_git_diff_is_tier2():
    assert _tier("git diff") == Tier.TWO


def test_git_show_is_tier2():
    assert _tier("git show HEAD") == Tier.TWO


def test_docker_ps_is_tier2():
    assert _tier("docker ps") == Tier.TWO


def test_docker_images_is_tier2():
    assert _tier("docker images") == Tier.TWO


def test_echo_is_tier2():
    assert _tier("echo hello") == Tier.TWO


def test_pip_list_is_tier2():
    assert _tier("pip list") == Tier.TWO


def test_pip_show_is_tier2():
    assert _tier("pip show requests") == Tier.TWO


def test_python_inline_is_tier2():
    assert _tier("python -c 'print(1+1)'") == Tier.TWO


def test_curl_is_tier2():
    assert _tier("curl https://example.com") == Tier.TWO


# ---------------------------------------------------------------------------
# classify_exec — Tier 2 (workspace-constrained)
# ---------------------------------------------------------------------------


def test_workspace_constrained_mv_is_tier2(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    working_dir = str(workspace)
    # mv within workspace: normally Tier 1, but workspace-constrained → Tier 2
    assert _tier("mv file1.txt file2.txt", workspace=workspace, working_dir=working_dir) == Tier.TWO


def test_workspace_constrained_python_script_is_tier2(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    working_dir = str(workspace)
    assert _tier("python analyze.py", workspace=workspace, working_dir=working_dir) == Tier.TWO


def test_workspace_constrained_unknown_cmd_is_tier2(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    working_dir = str(workspace)
    # An otherwise Tier 1 unknown command becomes Tier 2 in workspace
    assert _tier("make build", workspace=workspace, working_dir=working_dir) == Tier.TWO


def test_workspace_constrained_with_traversal_stays_tier1(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    working_dir = str(workspace)
    # Path traversal → NOT workspace-constrained
    assert _tier("cat ../../etc/passwd", workspace=workspace, working_dir=working_dir) == Tier.TWO
    # Note: cat is Tier 2 via text allowlist. Test traversal blocking with a non-allowlisted cmd:
    assert _tier("make ../../escape", workspace=workspace, working_dir=working_dir) == Tier.ONE


def test_workspace_constrained_with_sudo_stays_tier1(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    working_dir = str(workspace)
    assert _tier("sudo make install", workspace=workspace, working_dir=working_dir) == Tier.ONE


def test_workspace_constrained_rm_stays_tier1(tmp_path: Path):
    """rm is excluded from workspace-constrained Tier 2 — irreversible."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    working_dir = str(workspace)
    assert _tier("rm old_output.txt", workspace=workspace, working_dir=working_dir) == Tier.ONE


def test_workspace_constrained_pip_install_stays_tier1(tmp_path: Path):
    """pip install has host-level effects even from workspace working_dir."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    working_dir = str(workspace)
    assert _tier("pip install requests", workspace=workspace, working_dir=working_dir) == Tier.ONE


def test_workspace_constrained_outside_working_dir_stays_tier1(tmp_path: Path):
    """working_dir outside workspace → not workspace-constrained."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "other"
    outside.mkdir()
    assert _tier("mv file1 file2", workspace=workspace, working_dir=str(outside)) == Tier.ONE


def test_workspace_constrained_pipe_to_interpreter_stays_tier1(tmp_path: Path):
    """Pipe-to-interpreter check runs before workspace check."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    working_dir = str(workspace)
    assert _tier("echo x | bash", workspace=workspace, working_dir=working_dir) == Tier.ONE


# ---------------------------------------------------------------------------
# classify_tool — various tool names
# ---------------------------------------------------------------------------


def test_docker_exec_is_tier2():
    assert _tool_tier("docker_exec", {"code": "print(1)"}) == Tier.TWO


def test_read_file_is_tier2():
    assert _tool_tier("read_file", {"path": "/etc/hosts"}) == Tier.TWO


def test_list_dir_is_tier2():
    assert _tool_tier("list_dir", {"path": "/tmp"}) == Tier.TWO


def test_web_search_is_tier2():
    assert _tool_tier("web_search", {"query": "test"}) == Tier.TWO


def test_web_fetch_is_tier2():
    assert _tool_tier("web_fetch", {"url": "https://example.com"}) == Tier.TWO


def test_message_is_tier2():
    assert _tool_tier("message", {"text": "hello"}) == Tier.TWO


def test_report_task_is_tier2():
    assert _tool_tier("report_task", {}) == Tier.TWO


def test_session_approve_is_tier2():
    # session_approve must be Tier 2 — gating it would be recursive
    assert _tool_tier("session_approve", {"category": "exec", "reason": "test"}) == Tier.TWO


def test_write_file_in_workspace_is_tier2(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = str(workspace / "output.txt")
    assert _tool_tier("write_file", {"path": path, "content": "x"}, workspace=workspace) == Tier.TWO


def test_write_file_outside_workspace_is_tier1(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    assert _tool_tier("write_file", {"path": "/etc/hosts"}, workspace=workspace) == Tier.ONE


def test_write_file_large_overwrite_in_workspace_is_tier1(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    big_file = workspace / "big.bin"
    big_file.write_bytes(b"x" * 11_000)  # 11 KB > 10 KB threshold
    assert _tool_tier("write_file", {"path": str(big_file)}, workspace=workspace) == Tier.ONE


def test_edit_file_in_workspace_is_tier2(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = str(workspace / "notes.md")
    assert _tool_tier("edit_file", {"path": path}, workspace=workspace) == Tier.TWO


def test_edit_file_outside_workspace_is_tier1(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    assert _tool_tier("edit_file", {"path": "/root/important.md"}, workspace=workspace) == Tier.ONE


def test_spawn_is_tier1():
    assert _tool_tier("spawn", {"task": "do something"}) == Tier.ONE


def test_cron_is_tier1():
    assert _tool_tier("cron", {"schedule": "* * * * *", "command": "ls"}) == Tier.ONE


def test_unknown_tool_is_tier1():
    assert _tool_tier("my_custom_tool", {"arg": "value"}) == Tier.ONE


# ---------------------------------------------------------------------------
# classify_tool — GateDecision category field
# ---------------------------------------------------------------------------


def test_tier1_exec_has_exec_category():
    d = classify_tool("exec", {"command": "rm /tmp/file"})
    assert d.tier == Tier.ONE
    assert d.category == "exec"


def test_tier1_write_outside_workspace_has_write_category(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    d = classify_tool("write_file", {"path": "/root/x"}, workspace=workspace)
    assert d.tier == Tier.ONE
    assert d.category == "write"


def test_tier1_git_push_has_git_category():
    d = classify_exec("git push origin main")
    assert d.tier == Tier.ONE
    assert d.category == "git"


def test_tier1_pip_install_has_packages_category():
    d = classify_exec("pip install requests")
    assert d.tier == Tier.ONE
    assert d.category == "packages"


def test_tier1_spawn_has_spawn_category():
    d = classify_tool("spawn", {"task": "work"})
    assert d.tier == Tier.ONE
    assert d.category == "spawn"


# ---------------------------------------------------------------------------
# ToolRegistry — gate integration
# ---------------------------------------------------------------------------


async def test_registry_tier2_executes_normally():
    """A tool whose name the gate knows as Tier 2 executes without approval."""

    class ReadFileTestTool(Tool):
        @property
        def name(self) -> str:
            return "read_file"

        @property
        def description(self) -> str:
            return "read"

        @property
        def parameters(self) -> dict[str, Any]:
            return {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            }

        async def execute(self, path: str, **kwargs: Any) -> str:
            return f"read: {path}"

    reg = ToolRegistry()
    reg.register(ReadFileTestTool())
    result = await reg.execute("read_file", {"path": "/tmp/test.txt"})
    assert result == "read: /tmp/test.txt"


async def test_registry_unknown_tool_returns_error():
    reg = ToolRegistry()
    result = await reg.execute("no_such_tool", {})
    assert "not found" in result.lower()


async def test_registry_tier0_blocks_immediately():
    """Tier 0 exec command → hard reject, tool.execute() never called."""
    reg = ToolRegistry()
    # We don't register a real exec tool — the gate fires before lookup matters.
    # Simulate by classifying directly; for registry test use a fake exec tool.

    class FakeExecTool(Tool):
        executed = False

        @property
        def name(self):
            return "exec"

        @property
        def description(self):
            return "exec"

        @property
        def parameters(self):
            return {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            }

        async def execute(self, command: str, **kwargs: Any) -> str:
            FakeExecTool.executed = True
            return "should not reach here"

    reg.register(FakeExecTool())
    result = await reg.execute("exec", {"command": "rm -rf /"})
    assert "forbidden" in result.lower()
    assert FakeExecTool.executed is False


async def test_registry_tier1_defers_without_pre_approval():
    """Tier 1 tool call without pre-approval → deferred response, no execution."""

    class FakeExecTool(Tool):
        executed = False

        @property
        def name(self):
            return "exec"

        @property
        def description(self):
            return "exec"

        @property
        def parameters(self):
            return {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            }

        async def execute(self, command: str, **kwargs: Any) -> str:
            FakeExecTool.executed = True
            return "should not reach here"

    reg = ToolRegistry()
    reg.register(FakeExecTool())
    result = await reg.execute("exec", {"command": "rm /tmp/old.txt"})
    assert "approval" in result.lower()
    assert FakeExecTool.executed is False


async def test_registry_tier1_executes_after_pre_approval():
    """Tier 1 call succeeds once the matching category is pre-approved."""

    class FakeExecTool(Tool):
        @property
        def name(self):
            return "exec"

        @property
        def description(self):
            return "exec"

        @property
        def parameters(self):
            return {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            }

        async def execute(self, command: str, **kwargs: Any) -> str:
            return f"executed: {command}"

    reg = ToolRegistry()
    reg.register(FakeExecTool())
    reg.pre_approve("exec")
    result = await reg.execute("exec", {"command": "rm /tmp/old.txt"})
    assert "executed" in result


async def test_registry_pre_approve_does_not_unlock_tier0():
    """session_approve('exec') must not unlock Tier 0 commands."""

    class FakeExecTool(Tool):
        executed = False

        @property
        def name(self):
            return "exec"

        @property
        def description(self):
            return "exec"

        @property
        def parameters(self):
            return {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            }

        async def execute(self, command: str, **kwargs: Any) -> str:
            FakeExecTool.executed = True
            return "should not reach here"

    reg = ToolRegistry()
    reg.register(FakeExecTool())
    reg.pre_approve("exec")  # pre-approve exec category
    result = await reg.execute("exec", {"command": "rm -rf /"})  # Tier 0!
    assert "forbidden" in result.lower()
    assert FakeExecTool.executed is False


async def test_registry_receive_approval_returns_false_for_unknown_id():
    reg = ToolRegistry()
    found = await reg.receive_approval("nonexistent-id", True)
    assert found is False


async def test_registry_pre_approve_multiple_categories():
    """Pre-approving one category doesn't affect another."""
    reg = ToolRegistry()
    reg.pre_approve("exec")
    assert "exec" in reg._pre_approved
    assert "git" not in reg._pre_approved
    assert "write" not in reg._pre_approved
