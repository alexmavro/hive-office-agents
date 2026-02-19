"""DockerExecTool — run code in an isolated Docker sandbox.

The Queen uses this tool to execute Python code or shell commands in a
sandboxed container without touching the host environment.

Contrast with ExecTool (shell.py):
  - ExecTool:      host-level commands (hive cron add, ls, system tasks).
  - DockerExecTool: sandboxed code execution — ephemeral, isolated, safe.

The Queen should prefer docker_exec when:
  - Running code she wrote (test it safely)
  - Installing dependencies (pip install stays inside the container)
  - Executing user-provided or untrusted code

Before any Python code runs, the AST filter checks for sandbox-escape
patterns (calling docker/nsenter from inside the container) and syntax
errors. Shell commands skip the AST filter.
"""

from typing import Any

from hive.agent.tools.base import Tool
from hive.agent.sandbox.ast_filter import check_python
from hive.agent.sandbox.docker_sandbox import DockerSandbox, WORKER_IMAGE


class DockerExecTool(Tool):
    """
    Execute Python code or a shell command in an isolated Docker sandbox.

    Each call spins up a fresh ephemeral container that is automatically
    removed after execution. The container has:
      - Full network access (pip install, API calls work)
      - No access to host filesystem (only /sandbox is shared)
      - Memory and CPU limits to prevent runaway processes
      - Non-privilege escalation enforced

    Python code is AST-checked for sandbox-escape patterns before
    the container starts.
    """

    def __init__(
        self,
        image: str = WORKER_IMAGE,
        memory: str = "512m",
        cpus: str = "1.0",
        default_timeout: int = 60,
    ) -> None:
        self._sandbox = DockerSandbox(
            image=image,
            memory=memory,
            cpus=cpus,
            default_timeout=default_timeout,
        )

    @staticmethod
    def is_available(image: str = WORKER_IMAGE) -> bool:
        """Return True if Docker daemon is running and the worker image exists."""
        return DockerSandbox.is_available(image)

    @property
    def name(self) -> str:
        return "docker_exec"

    @property
    def description(self) -> str:
        return (
            "Execute Python code or a shell command in an isolated Docker sandbox. "
            "Use this instead of 'exec' when you want to run code safely without "
            "affecting the host system. "
            "The container has full network access — you can use pip install. "
            "Files written to /sandbox are available during the run. "
            "Each call starts a fresh container that is removed when done."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": (
                        "The code or command to execute. "
                        "For Python: full source code. "
                        "For shell: a shell command string (e.g. 'pip install pandas && python -c \"import pandas\"')."
                    ),
                },
                "language": {
                    "type": "string",
                    "enum": ["python", "shell"],
                    "description": "Language to run. 'python' runs via `python /sandbox/run.py`. 'shell' runs via `sh -c`.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds. Default: 60. Use higher values for pip installs (e.g. 120).",
                },
            },
            "required": ["code"],
        }

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int | None = None,
        **kwargs: Any,
    ) -> str:
        language = language.lower()

        if language not in ("python", "shell"):
            return f"Error: unsupported language '{language}'. Use 'python' or 'shell'."

        if language == "python":
            violations = check_python(code)
            if violations:
                lines = "\n".join(f"  - {v}" for v in violations)
                return (
                    f"Error: Code blocked by sandbox safety check.\n"
                    f"Violations detected:\n{lines}\n\n"
                    f"If you need to run Docker commands from inside the sandbox, "
                    f"that is not permitted (sandbox escape). Use the host 'exec' tool instead."
                )
            result = await self._sandbox.run_python(code, timeout=timeout)
        else:
            result = await self._sandbox.run_shell(code, timeout=timeout)

        return result.to_tool_output()
