"""Tests for the AST filter."""

import pytest
from hive.agent.sandbox.ast_filter import ASTViolation, check_python


# --- Clean code ---

def test_empty_code_is_clean():
    assert check_python("") == []


def test_whitespace_only_is_clean():
    assert check_python("   \n  \t  ") == []


def test_simple_print_is_clean():
    code = 'print("hello world")'
    assert check_python(code) == []


def test_math_is_clean():
    code = "result = (2 + 3) * 10\nprint(result)"
    assert check_python(code) == []


def test_regular_subprocess_is_clean():
    """subprocess.run(['python', '--version']) is fine — Docker sandboxes it."""
    code = "import subprocess\nsubprocess.run(['python', '--version'])"
    assert check_python(code) == []


def test_import_os_is_clean():
    """import os is fine — only specific dangerous calls are blocked."""
    code = "import os\nprint(os.getcwd())"
    assert check_python(code) == []


def test_requests_is_clean():
    """Network calls are fine — container has network access."""
    code = "import requests\nr = requests.get('https://example.com')\nprint(r.status_code)"
    assert check_python(code) == []


def test_pandas_is_clean():
    code = "import pandas as pd\ndf = pd.DataFrame({'a': [1, 2, 3]})\nprint(df)"
    assert check_python(code) == []


def test_pip_subprocess_is_clean():
    """pip install via subprocess is fine — it's what the Queen does in the sandbox."""
    code = "import subprocess\nsubprocess.run(['pip', 'install', 'requests'])"
    assert check_python(code) == []


# --- Syntax errors ---

def test_syntax_error_caught():
    code = "def foo(:\n    pass"
    violations = check_python(code)
    assert len(violations) == 1
    assert violations[0].node_type == "SyntaxError"


def test_syntax_error_has_line_number():
    code = "x = (\n  1 +\n  )\n"
    violations = check_python(code)
    assert violations[0].node_type == "SyntaxError"
    assert violations[0].line >= 0


# --- Sandbox escape attempts ---

def test_docker_subprocess_list_blocked():
    code = "import subprocess\nsubprocess.run(['docker', 'run', '-v', '/:/host', 'alpine'])"
    violations = check_python(code)
    assert any(v.node_type == "SandboxEscape" for v in violations)


def test_docker_subprocess_shell_blocked():
    code = "import subprocess\nsubprocess.run('docker run -v /:/host alpine', shell=True)"
    violations = check_python(code)
    assert any(v.node_type == "SandboxEscape" for v in violations)


def test_nsenter_blocked():
    code = "import subprocess\nsubprocess.run(['nsenter', '-t', '1', '-m', '-u', '-i', '-n', '-p'])"
    violations = check_python(code)
    assert any(v.node_type == "SandboxEscape" for v in violations)


def test_chroot_blocked():
    code = "import subprocess\nsubprocess.run(['chroot', '/host'])"
    violations = check_python(code)
    assert any(v.node_type == "SandboxEscape" for v in violations)


def test_popen_docker_blocked():
    code = "from subprocess import Popen\nPopen(['docker', 'exec', '-it', 'container', 'bash'])"
    violations = check_python(code)
    assert any(v.node_type == "SandboxEscape" for v in violations)


# --- Fork bomb patterns ---

def test_os_fork_blocked():
    code = "import os\nos.fork()"
    violations = check_python(code)
    assert any(v.node_type == "DangerousOsCall" for v in violations)


def test_os_execv_blocked():
    code = "import os\nos.execv('/bin/sh', ['/bin/sh'])"
    violations = check_python(code)
    assert any(v.node_type == "DangerousOsCall" for v in violations)


def test_os_forkpty_blocked():
    code = "import os\nos.forkpty()"
    violations = check_python(code)
    assert any(v.node_type == "DangerousOsCall" for v in violations)


# --- Violation properties ---

def test_violation_has_line_number():
    code = "import subprocess\nsubprocess.run(['docker', 'run', 'alpine'])"
    violations = check_python(code)
    violation = next(v for v in violations if v.node_type == "SandboxEscape")
    assert violation.line == 2


def test_violation_str_includes_line():
    v = ASTViolation(node_type="SandboxEscape", description="test", line=42)
    assert "42" in str(v)
    assert "SandboxEscape" in str(v)


def test_multiple_violations_detected():
    code = (
        "import subprocess\n"
        "subprocess.run(['docker', 'run', 'alpine'])\n"
        "import os\n"
        "os.fork()\n"
    )
    violations = check_python(code)
    node_types = {v.node_type for v in violations}
    assert "SandboxEscape" in node_types
    assert "DangerousOsCall" in node_types
