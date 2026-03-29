"""Tiny test plugin for subprocess integration tests."""


def echo(message: str = "") -> dict:
    """Return the message back."""
    return {"echoed": message}


def add(a: int = 0, b: int = 0) -> dict:
    """Add two numbers."""
    return {"sum": a + b}


def fail() -> None:
    """Intentionally raise an error."""
    raise ValueError("intentional test error")
