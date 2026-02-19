"""Tests for DockerExecTool.

Unit tests mock the sandbox — no Docker image required.
Integration tests are marked @pytest.mark.docker.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from hive.agent.tools.docker_exec import DockerExecTool
from hive.agent.sandbox.docker_sandbox import SandboxResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _success_result(stdout: str = "ok\n") -> SandboxResult:
    return SandboxResult(stdout=stdout, stderr="", exit_code=0, timed_out=False)


def _error_result(stderr: str = "error\n", exit_code: int = 1) -> SandboxResult:
    return SandboxResult(stdout="", stderr=stderr, exit_code=exit_code, timed_out=False)


def _timeout_result() -> SandboxResult:
    return SandboxResult(stdout="", stderr="", exit_code=-1, timed_out=True)


# ---------------------------------------------------------------------------
# Tool metadata tests
# ---------------------------------------------------------------------------

def test_tool_name():
    tool = DockerExecTool()
    assert tool.name == "docker_exec"


def test_tool_has_description():
    tool = DockerExecTool()
    assert len(tool.description) > 20


def test_tool_parameters_have_code():
    tool = DockerExecTool()
    assert "code" in tool.parameters["properties"]
    assert "code" in tool.parameters["required"]


def test_tool_parameters_have_language():
    tool = DockerExecTool()
    assert "language" in tool.parameters["properties"]


def test_tool_parameters_have_timeout():
    tool = DockerExecTool()
    assert "timeout" in tool.parameters["properties"]


# ---------------------------------------------------------------------------
# AST filter integration — blocked before container starts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_docker_escape_blocked():
    """Code that calls docker from inside should be blocked before execution."""
    tool = DockerExecTool()
    code = "import subprocess\nsubprocess.run(['docker', 'run', '-v', '/:/host', 'alpine'])"

    with patch.object(tool._sandbox, "run_python", new_callable=AsyncMock) as mock_run:
        result = await tool.execute(code=code, language="python")

    mock_run.assert_not_called()
    assert "blocked" in result.lower()
    assert "SandboxEscape" in result


@pytest.mark.asyncio
async def test_syntax_error_blocked():
    """Syntax errors should be caught before container spin-up."""
    tool = DockerExecTool()
    code = "def bad(:\n    pass"

    with patch.object(tool._sandbox, "run_python", new_callable=AsyncMock) as mock_run:
        result = await tool.execute(code=code, language="python")

    mock_run.assert_not_called()
    assert "blocked" in result.lower()


@pytest.mark.asyncio
async def test_clean_python_reaches_sandbox():
    """Clean code should pass the AST filter and be sent to Docker."""
    tool = DockerExecTool()
    code = "print('hello')"

    with patch.object(tool._sandbox, "run_python", new_callable=AsyncMock, return_value=_success_result("hello\n")) as mock_run:
        result = await tool.execute(code=code, language="python")

    mock_run.assert_called_once()
    assert "hello" in result


# ---------------------------------------------------------------------------
# Language routing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_python_routes_to_run_python():
    tool = DockerExecTool()

    with patch.object(tool._sandbox, "run_python", new_callable=AsyncMock, return_value=_success_result()) as mock_python, \
         patch.object(tool._sandbox, "run_shell", new_callable=AsyncMock) as mock_shell:
        await tool.execute(code="print(1)", language="python")

    mock_python.assert_called_once()
    mock_shell.assert_not_called()


@pytest.mark.asyncio
async def test_shell_routes_to_run_shell():
    tool = DockerExecTool()

    with patch.object(tool._sandbox, "run_python", new_callable=AsyncMock) as mock_python, \
         patch.object(tool._sandbox, "run_shell", new_callable=AsyncMock, return_value=_success_result()) as mock_shell:
        await tool.execute(code="echo hi", language="shell")

    mock_shell.assert_called_once()
    mock_python.assert_not_called()


@pytest.mark.asyncio
async def test_shell_skips_ast_filter():
    """Shell commands are not Python — AST filter must not be applied."""
    tool = DockerExecTool()
    # 'docker' in a shell command would be caught by AST filter if applied to shell
    # but shell routes to run_shell directly
    with patch.object(tool._sandbox, "run_shell", new_callable=AsyncMock, return_value=_success_result("ok")) as mock_shell:
        result = await tool.execute(code="echo ok", language="shell")

    mock_shell.assert_called_once()
    assert "ok" in result


@pytest.mark.asyncio
async def test_default_language_is_python():
    """language parameter defaults to python if not supplied."""
    tool = DockerExecTool()

    with patch.object(tool._sandbox, "run_python", new_callable=AsyncMock, return_value=_success_result()) as mock_python:
        await tool.execute(code="print(1)")

    mock_python.assert_called_once()


@pytest.mark.asyncio
async def test_invalid_language_returns_error():
    tool = DockerExecTool()
    result = await tool.execute(code="print(1)", language="ruby")
    assert "unsupported" in result.lower()


# ---------------------------------------------------------------------------
# Timeout forwarding
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_timeout_forwarded_to_sandbox():
    tool = DockerExecTool()

    with patch.object(tool._sandbox, "run_python", new_callable=AsyncMock, return_value=_success_result()) as mock_run:
        await tool.execute(code="print(1)", timeout=120)

    _, kwargs = mock_run.call_args
    assert kwargs.get("timeout") == 120 or mock_run.call_args[0][1] == 120


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_timeout_result_reported():
    tool = DockerExecTool()

    with patch.object(tool._sandbox, "run_python", new_callable=AsyncMock, return_value=_timeout_result()):
        result = await tool.execute(code="import time; time.sleep(999)")

    assert "timed out" in result.lower()


@pytest.mark.asyncio
async def test_stderr_in_output():
    tool = DockerExecTool()

    with patch.object(tool._sandbox, "run_python", new_callable=AsyncMock, return_value=_error_result(stderr="something went wrong\n")):
        result = await tool.execute(code="raise ValueError('x')")

    assert "something went wrong" in result


# ---------------------------------------------------------------------------
# Integration tests — require hive-worker image
# ---------------------------------------------------------------------------

from hive.agent.sandbox.docker_sandbox import WORKER_IMAGE
docker_mark = pytest.mark.skipif(
    not DockerExecTool.is_available(),
    reason=f"hive-worker image not built (run: docker build -f worker.Dockerfile -t {WORKER_IMAGE} .)",
)


@docker_mark
@pytest.mark.asyncio
async def test_integration_python_runs():
    tool = DockerExecTool()
    result = await tool.execute(code='print("from docker exec tool")')
    assert "from docker exec tool" in result


@docker_mark
@pytest.mark.asyncio
async def test_integration_shell_runs():
    tool = DockerExecTool()
    result = await tool.execute(code="echo 'shell via docker exec'", language="shell")
    assert "shell via docker exec" in result


@docker_mark
@pytest.mark.asyncio
async def test_integration_pip_install():
    tool = DockerExecTool()
    result = await tool.execute(
        code=(
            "import subprocess, sys\n"
            "subprocess.run([sys.executable, '-m', 'pip', 'install', 'cowsay'], check=True)\n"
            "import cowsay; cowsay.cow('S3 works')\n"
        ),
        timeout=120,
    )
    assert "S3 works" in result, f"Unexpected output: {result}"
