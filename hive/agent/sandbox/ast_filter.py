"""AST filter — parse and validate Python code before execution.

First line of defense: catch dangerous patterns before Docker even starts.
Docker provides the real isolation; this layer catches:
  - Syntax errors (cheap fail before container spin-up)
  - Docker-escape attempts (subprocess calling docker/nsenter/chroot)
  - Fork bombs (os.fork() in tight loops)

Not intended to be a comprehensive security filter — Docker handles that.
Goal: catch the obvious, fast.
"""

import ast
from dataclasses import dataclass


# Commands that would let code escape the Docker sandbox by reaching the host
_ESCAPE_COMMANDS = frozenset({
    "docker",
    "nsenter",
    "chroot",
    "unshare",
    "runc",
    "containerd",
    "ctr",
})

# os module calls that are dangerous even in containers (fork bombs, exec replacement)
_DANGEROUS_OS_CALLS = frozenset({
    "fork",
    "forkpty",
    "execv",
    "execve",
    "execvp",
    "execvpe",
    "execl",
    "execle",
    "execlp",
    "execlpe",
})


@dataclass
class ASTViolation:
    """A detected dangerous pattern in Python code."""
    node_type: str
    description: str
    line: int

    def __str__(self) -> str:
        return f"Line {self.line}: [{self.node_type}] {self.description}"


def check_python(code: str) -> list[ASTViolation]:
    """
    Parse and check Python code for dangerous patterns.

    Args:
        code: Python source code to check.

    Returns:
        List of violations. Empty list means no issues detected.
        Syntax errors appear as violations with node_type="SyntaxError".
    """
    if not code or not code.strip():
        return []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [ASTViolation(
            node_type="SyntaxError",
            description=str(e),
            line=e.lineno or 0,
        )]

    checker = _Checker()
    checker.visit(tree)
    return checker.violations


class _Checker(ast.NodeVisitor):
    """AST visitor that collects violations."""

    def __init__(self) -> None:
        self.violations: list[ASTViolation] = []

    def _add(self, node: ast.AST, node_type: str, description: str) -> None:
        line = getattr(node, "lineno", 0)
        self.violations.append(ASTViolation(node_type, description, line))

    def visit_Call(self, node: ast.Call) -> None:
        """Detect dangerous function calls."""
        self._check_call(node)
        self.generic_visit(node)

    def _check_call(self, node: ast.Call) -> None:
        func = node.func

        # subprocess.run(["docker", ...]) / subprocess.Popen(["nsenter", ...])
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name) and func.value.id == "subprocess":
                self._check_subprocess_args(node)

            # os.fork(), os.execv(), etc.
            elif isinstance(func.value, ast.Name) and func.value.id == "os":
                if func.attr in _DANGEROUS_OS_CALLS:
                    self._add(
                        node,
                        "DangerousOsCall",
                        f"os.{func.attr}() can cause fork bombs or replace the process image",
                    )

        # Direct subprocess() calls (e.g. from `from subprocess import run`)
        elif isinstance(func, ast.Name) and func.id in ("Popen", "run", "call", "check_call", "check_output"):
            self._check_subprocess_args(node)

    def _check_subprocess_args(self, node: ast.Call) -> None:
        """Check if subprocess call targets an escape command."""
        if not node.args:
            return

        first_arg = node.args[0]

        # subprocess.run(["docker", "run", ...])
        if isinstance(first_arg, ast.List) and first_arg.elts:
            cmd_node = first_arg.elts[0]
            if isinstance(cmd_node, ast.Constant) and isinstance(cmd_node.value, str):
                cmd = cmd_node.value.strip().lower()
                if cmd in _ESCAPE_COMMANDS:
                    self._add(
                        node,
                        "SandboxEscape",
                        f"Calling '{cmd}' via subprocess can escape the Docker sandbox",
                    )

        # subprocess.run("docker run ...", shell=True)
        elif isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            cmd = first_arg.value.strip().lower().split()[0] if first_arg.value.strip() else ""
            if cmd in _ESCAPE_COMMANDS:
                self._add(
                    node,
                    "SandboxEscape",
                    f"Calling '{cmd}' via subprocess can escape the Docker sandbox",
                )
