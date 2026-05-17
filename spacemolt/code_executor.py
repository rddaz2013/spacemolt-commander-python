"""Sandboxed code executor for token-optimised data processing.

Instead of loading large datasets into the LLM context, the agent
generates Python code that processes data locally and returns a
compact summary.  AST validation blocks dangerous imports.
"""

from __future__ import annotations

import ast
import asyncio
import io
import json
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Optional

from spacemolt.ui import log_info, log_error

# Imports that are never allowed inside generated code
BLOCKED_IMPORTS = frozenset({
    "os", "subprocess", "shutil", "sys", "signal",
    "ctypes", "importlib", "pathlib", "socket",
    "multiprocessing", "threading",
    "__builtin__", "builtins",
})

# Modules pre-injected into the execution namespace
ALLOWED_MODULES = {
    "json": json,
    "math": __import__("math"),
    "statistics": __import__("statistics"),
    "re": __import__("re"),
    "collections": __import__("collections"),
    "itertools": __import__("itertools"),
    "functools": __import__("functools"),
    "datetime": __import__("datetime"),
}

MAX_EXEC_TIME = 30  # seconds
MAX_OUTPUT_LEN = 4_000  # chars


class CodeExecutionError(Exception):
    pass


# ---------------------------------------------------------------------------
# AST validation
# ---------------------------------------------------------------------------

def validate_code(source: str) -> tuple[bool, Optional[str]]:
    """Parse *source* and reject dangerous constructs.

    Returns ``(True, None)`` on success, ``(False, reason)`` on failure.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return False, f"Syntax error: {exc}"

    for node in ast.walk(tree):
        # Block dangerous imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in BLOCKED_IMPORTS:
                    return False, f"Import of '{alias.name}' is blocked"

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in BLOCKED_IMPORTS:
                    return False, f"Import from '{node.module}' is blocked"

        # Block eval / exec / compile calls
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in ("eval", "exec", "compile", "__import__"):
                return False, f"Call to '{func.id}()' is blocked"

        # Block attribute access to __dunder__ methods (escape hatches)
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                if node.attr not in ("__len__", "__str__", "__repr__", "__init__"):
                    return False, f"Access to '{node.attr}' is blocked"

    return True, None


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class CodeExecutor:
    """Execute LLM-generated Python in a restricted namespace."""

    def __init__(self, api_client: Any = None) -> None:
        self._api = api_client

    async def execute(self, code: str, extra_context: Optional[dict] = None) -> str:
        """Validate and run *code*, returning the result string."""
        # 1) Validate
        ok, reason = validate_code(code)
        if not ok:
            raise CodeExecutionError(f"Code validation failed: {reason}")

        # 2) Build namespace
        namespace: dict[str, Any] = {}
        namespace.update(ALLOWED_MODULES)
        if self._api is not None:
            namespace["api"] = self._api
        if extra_context:
            namespace.update(extra_context)

        # Capture stdout
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        # 3) Execute with timeout
        log_info("Executing generated code…")

        def _run() -> None:
            compiled = compile(code, "<agent-code>", "exec")
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(compiled, namespace)  # noqa: S102 — intentional, guarded by AST validation

        try:
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, _run),
                timeout=MAX_EXEC_TIME,
            )
        except asyncio.TimeoutError:
            raise CodeExecutionError(f"Code execution timed out after {MAX_EXEC_TIME}s")
        except Exception as exc:
            tb = traceback.format_exc()
            raise CodeExecutionError(f"Runtime error: {exc}\n{tb}")

        # 4) Collect result
        result = namespace.get("result")
        stdout = stdout_buf.getvalue()

        if result is not None:
            if isinstance(result, (dict, list)):
                output = json.dumps(result, indent=2, default=str)
            else:
                output = str(result)
        elif stdout:
            output = stdout
        else:
            output = "(code executed successfully, no 'result' variable set)"

        # Truncate
        if len(output) > MAX_OUTPUT_LEN:
            output = output[:MAX_OUTPUT_LEN] + "\n… [truncated]"

        return output
