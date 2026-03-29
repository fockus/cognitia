"""Code execution tool for Cognitia MCP server."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def exec_code(code: str, timeout_seconds: int = 30) -> dict[str, Any]:
    """Execute Python code in a subprocess and return stdout/stderr.

    Uses asyncio.create_subprocess_exec with python -c for isolation.
    Captures stdout and stderr separately.
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "python",
            "-c",
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {
                "ok": False,
                "error": f"Execution timed out after {timeout_seconds}s",
                "data": {"timeout": True},
            }

        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        if process.returncode == 0:
            return {
                "ok": True,
                "data": {
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "returncode": 0,
                },
            }
        else:
            return {
                "ok": False,
                "error": stderr_str or f"Process exited with code {process.returncode}",
                "data": {
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "returncode": process.returncode,
                },
            }
    except Exception as exc:
        logger.warning("exec_code_failed", error=str(exc))
        return {"ok": False, "error": str(exc)}
