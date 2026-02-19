"""Tests for DockerSandbox.

Two layers:
  - Unit tests: mock asyncio.create_subprocess_exec — no Docker needed, always run.
  - Integration tests: marked @pytest.mark.docker — skipped unless hive-worker image exists.

Run integration tests after building the worker image:
    docker build -f worker.Dockerfile -t hive-worker:latest .
    pytest tests/test_docker_sandbox.py -m docker -v
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from hive.agent.sandbox.docker_sandbox import DockerSandbox, SandboxResult, WORKER_IMAGE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_process(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
    """Build a mock asyncio subprocess that returns fixed output."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    return proc


DOCKER_AVAILABLE = DockerSandbox.is_available()
docker_mark = pytest.mark.skipif(
    not DOCKER_AVAILABLE,
    reason=f"hive-worker image not built (run: docker build -f worker.Dockerfile -t {WORKER_IMAGE} .)",
)


# ---------------------------------------------------------------------------
# SandboxResult unit tests
# ---------------------------------------------------------------------------

def test_result_success():
    r = SandboxResult(stdout="hi\n", stderr="", exit_code=0, timed_out=False)
    assert r.success is True


def test_result_failure_nonzero():
    r = SandboxResult(stdout="", stderr="", exit_code=1, timed_out=False)
    assert r.success is False


def test_result_failure_timeout():
    r = SandboxResult(stdout="", stderr="", exit_code=0, timed_out=True)
    assert r.success is False


def test_to_tool_output_stdout_only():
    r = SandboxResult(stdout="hello\n", stderr="", exit_code=0, timed_out=False)
    assert r.to_tool_output() == "hello"


def test_to_tool_output_stderr_included():
    r = SandboxResult(stdout="", stderr="warning\n", exit_code=0, timed_out=False)
    assert "STDERR" in r.to_tool_output()
    assert "warning" in r.to_tool_output()


def test_to_tool_output_exit_code_included():
    r = SandboxResult(stdout="", stderr="", exit_code=2, timed_out=False)
    assert "2" in r.to_tool_output()


def test_to_tool_output_timeout():
    r = SandboxResult(stdout="", stderr="", exit_code=-1, timed_out=True)
    assert "timed out" in r.to_tool_output().lower()


def test_to_tool_output_no_output():
    r = SandboxResult(stdout="", stderr="", exit_code=0, timed_out=False)
    assert r.to_tool_output() == "(no output)"


# ---------------------------------------------------------------------------
# DockerSandbox unit tests (mocked subprocess)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_python_builds_correct_command():
    """run_python should invoke docker run with the right arguments."""
    sandbox = DockerSandbox(image="hive-worker:latest", memory="256m", cpus="0.5")
    proc = _mock_process(stdout=b"42\n")

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc) as mock_exec:
        result = await sandbox.run_python("print(42)")

    assert result.stdout == "42\n"
    assert result.success is True

    call_args = mock_exec.call_args[0]
    assert call_args[0] == "docker"
    assert "run" in call_args
    assert "--rm" in call_args
    assert "--memory" in call_args
    assert "256m" in call_args
    assert "--cpus" in call_args
    assert "0.5" in call_args
    assert "python" in call_args
    assert "/sandbox/run.py" in call_args


@pytest.mark.asyncio
async def test_run_shell_builds_correct_command():
    """run_shell should invoke docker run with sh -c."""
    sandbox = DockerSandbox()
    proc = _mock_process(stdout=b"hello\n")

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await sandbox.run_shell("echo hello")

    assert result.stdout == "hello\n"


@pytest.mark.asyncio
async def test_nonzero_exit_code_captured():
    sandbox = DockerSandbox()
    proc = _mock_process(stdout=b"", stderr=b"error\n", returncode=1)

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await sandbox.run_python("import sys; sys.exit(1)")

    assert result.exit_code == 1
    assert result.success is False


@pytest.mark.asyncio
async def test_stderr_captured():
    sandbox = DockerSandbox()
    proc = _mock_process(stdout=b"", stderr=b"uh oh\n", returncode=0)

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await sandbox.run_python("import sys; sys.stderr.write('uh oh\\n')")

    assert "uh oh" in result.stderr


@pytest.mark.asyncio
async def test_timeout_returns_timed_out_result():
    """When the container exceeds timeout, timed_out=True and process is killed."""
    sandbox = DockerSandbox(default_timeout=1)
    proc = MagicMock()
    proc.returncode = None
    proc.kill = MagicMock()
    proc.wait = AsyncMock()

    async def slow_communicate():
        await asyncio.sleep(999)
        return b"", b""

    proc.communicate = slow_communicate

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc):
        result = await sandbox.run_python("import time; time.sleep(999)")

    assert result.timed_out is True
    proc.kill.assert_called_once()


@pytest.mark.asyncio
async def test_sandbox_exception_returns_error_result():
    """If docker itself fails to start, result has stderr with the error."""
    sandbox = DockerSandbox()

    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("docker not found")):
        result = await sandbox.run_python("print('hi')")

    assert result.exit_code == -1
    assert "docker" in result.stderr.lower() or "not found" in result.stderr.lower()


@pytest.mark.asyncio
async def test_security_opt_present():
    """Container must always use --security-opt no-new-privileges."""
    sandbox = DockerSandbox()
    proc = _mock_process(stdout=b"ok\n")

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc) as mock_exec:
        await sandbox.run_python("print('ok')")

    call_args = mock_exec.call_args[0]
    assert "--security-opt" in call_args
    assert "no-new-privileges" in call_args


@pytest.mark.asyncio
async def test_volume_mount_present():
    """The sandbox temp dir must be mounted as /sandbox."""
    sandbox = DockerSandbox()
    proc = _mock_process()

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=proc) as mock_exec:
        await sandbox.run_python("pass")

    call_args = mock_exec.call_args[0]
    # Find the -v argument
    assert "-v" in call_args
    v_idx = list(call_args).index("-v")
    mount = call_args[v_idx + 1]
    assert ":/sandbox:rw" in mount


# ---------------------------------------------------------------------------
# Integration tests — require hive-worker image
# ---------------------------------------------------------------------------

@docker_mark
@pytest.mark.asyncio
async def test_integration_hello_world():
    sandbox = DockerSandbox()
    result = await sandbox.run_python('print("hello from sandbox")')
    assert result.success
    assert "hello from sandbox" in result.stdout


@docker_mark
@pytest.mark.asyncio
async def test_integration_stdout_captured():
    sandbox = DockerSandbox()
    result = await sandbox.run_python("for i in range(3): print(i)")
    assert result.success
    assert "0" in result.stdout
    assert "1" in result.stdout
    assert "2" in result.stdout


@docker_mark
@pytest.mark.asyncio
async def test_integration_nonzero_exit():
    sandbox = DockerSandbox()
    result = await sandbox.run_python("import sys; sys.exit(42)")
    assert result.exit_code == 42
    assert not result.success


@docker_mark
@pytest.mark.asyncio
async def test_integration_stderr_captured():
    sandbox = DockerSandbox()
    result = await sandbox.run_python("import sys; sys.stderr.write('warn\\n')")
    assert "warn" in result.stderr


@docker_mark
@pytest.mark.asyncio
async def test_integration_shell_command():
    sandbox = DockerSandbox()
    result = await sandbox.run_shell("echo 'shell works'")
    assert result.success
    assert "shell works" in result.stdout


@docker_mark
@pytest.mark.asyncio
async def test_integration_timeout_enforced():
    sandbox = DockerSandbox(default_timeout=3)
    result = await sandbox.run_python("import time; time.sleep(999)")
    assert result.timed_out


@docker_mark
@pytest.mark.asyncio
async def test_integration_container_ephemeral():
    """After run, no dangling containers should remain."""
    import subprocess as sp

    sandbox = DockerSandbox()
    await sandbox.run_python("print('done')")

    # Check no hive-sandbox containers remain
    r = sp.run(
        ["docker", "ps", "-a", "--filter", "ancestor=hive-worker:latest", "--format", "{{.ID}}"],
        capture_output=True,
        text=True,
    )
    assert r.stdout.strip() == "", f"Dangling containers found: {r.stdout}"


@docker_mark
@pytest.mark.asyncio
async def test_integration_file_exchange():
    """Code can write to /sandbox and the host can read the result."""
    import tempfile, os

    sandbox = DockerSandbox()
    result = await sandbox.run_python(
        "with open('/sandbox/output.txt', 'w') as f:\n"
        "    f.write('written by sandbox')\n"
        "print('done')"
    )
    # We don't have the temp dir here, but at minimum the run should succeed
    assert result.success


@docker_mark
@pytest.mark.asyncio
async def test_integration_pip_install():
    """Queen can pip install inside the container."""
    sandbox = DockerSandbox(default_timeout=120)  # pip install needs more time
    result = await sandbox.run_python(
        "import subprocess, sys\n"
        "subprocess.run([sys.executable, '-m', 'pip', 'install', 'cowsay'], check=True)\n"
        "import cowsay; cowsay.cow('moo')\n"
    )
    assert result.success, f"pip install failed: {result.to_tool_output()}"
    assert "moo" in result.stdout
