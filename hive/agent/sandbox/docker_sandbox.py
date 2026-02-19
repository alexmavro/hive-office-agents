"""DockerSandbox — ephemeral Docker containers for safe code execution.

Design:
- Each run creates a fresh container, mounts a temp dir as /sandbox, runs, removes.
- Full network access (Queen needs pip install, API calls inside the sandbox).
- Isolation is filesystem-only: container can't touch host paths outside /sandbox.
- Resource limits prevent runaway processes (memory, CPUs).
- Code is written to a file in the temp dir — avoids quote-escaping issues.

Usage:
    sandbox = DockerSandbox()
    result = await sandbox.run_python("import sys; print(sys.version)")
    print(result.to_tool_output())
"""

import asyncio
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


WORKER_IMAGE = "hive-worker:latest"


@dataclass
class SandboxResult:
    """Result from a sandbox execution."""
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def to_tool_output(self) -> str:
        """Format result for LLM consumption."""
        if self.timed_out:
            return "Error: Execution timed out"

        parts = []
        if self.stdout:
            parts.append(self.stdout.rstrip())
        if self.stderr.strip():
            parts.append(f"STDERR:\n{self.stderr.rstrip()}")
        if self.exit_code != 0:
            parts.append(f"Exit code: {self.exit_code}")

        return "\n".join(parts) if parts else "(no output)"


class DockerSandbox:
    """
    Runs code in ephemeral Docker containers.

    Args:
        image:           Docker image to use. Must be pre-built (see worker.Dockerfile).
        memory:          Container memory limit (Docker format: '512m', '1g').
        cpus:            CPU limit (e.g. '1.0' = one core).
        default_timeout: Default execution timeout in seconds.
    """

    def __init__(
        self,
        image: str = WORKER_IMAGE,
        memory: str = "512m",
        cpus: str = "1.0",
        default_timeout: int = 60,
    ) -> None:
        self.image = image
        self.memory = memory
        self.cpus = cpus
        self.default_timeout = default_timeout

    @staticmethod
    def is_available(image: str = WORKER_IMAGE) -> bool:
        """
        Check whether the sandbox can run.

        Returns True only if both the Docker daemon is reachable AND
        the worker image has been built.
        """
        try:
            r = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
            )
            if r.returncode != 0:
                return False
        except Exception:
            return False

        try:
            r = subprocess.run(
                ["docker", "image", "inspect", image],
                capture_output=True,
                timeout=5,
            )
            return r.returncode == 0
        except Exception:
            return False

    async def run_python(
        self,
        code: str,
        timeout: int | None = None,
    ) -> SandboxResult:
        """
        Execute Python code in a sandboxed container.

        The code is written to /sandbox/run.py inside the container.
        The /sandbox directory is also available for file exchange.
        """
        t = timeout if timeout is not None else self.default_timeout
        sandbox_dir = tempfile.mkdtemp(prefix="hive-sandbox-")
        try:
            Path(sandbox_dir, "run.py").write_text(code, encoding="utf-8")
            return await self._run_container(
                sandbox_dir=sandbox_dir,
                cmd=["python", "/sandbox/run.py"],
                timeout=t,
            )
        finally:
            shutil.rmtree(sandbox_dir, ignore_errors=True)

    async def run_shell(
        self,
        command: str,
        timeout: int | None = None,
    ) -> SandboxResult:
        """
        Execute a shell command in a sandboxed container.

        The /sandbox directory is available for file exchange.
        """
        t = timeout if timeout is not None else self.default_timeout
        sandbox_dir = tempfile.mkdtemp(prefix="hive-sandbox-")
        try:
            return await self._run_container(
                sandbox_dir=sandbox_dir,
                cmd=["sh", "-c", command],
                timeout=t,
            )
        finally:
            shutil.rmtree(sandbox_dir, ignore_errors=True)

    async def _run_container(
        self,
        sandbox_dir: str,
        cmd: list[str],
        timeout: int,
    ) -> SandboxResult:
        """
        Spin up an ephemeral container, run cmd, capture output, tear down.

        Container flags:
          --rm                       auto-remove on exit
          --memory / --cpus          resource limits
          --security-opt             no privilege escalation
          -v sandbox_dir:/sandbox    file exchange only — host is not exposed
        """
        docker_cmd = [
            "docker", "run",
            "--rm",
            "--memory", self.memory,
            "--cpus", self.cpus,
            "--security-opt", "no-new-privileges",
            "-v", f"{sandbox_dir}:/sandbox:rw",
            self.image,
        ] + cmd

        try:
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=float(timeout),
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                return SandboxResult(
                    stdout="",
                    stderr="",
                    exit_code=-1,
                    timed_out=True,
                )

            return SandboxResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                exit_code=process.returncode or 0,
                timed_out=False,
            )

        except Exception as exc:
            return SandboxResult(
                stdout="",
                stderr=f"Docker error: {exc}",
                exit_code=-1,
                timed_out=False,
            )
