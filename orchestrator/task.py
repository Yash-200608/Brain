"""Compatibility shim — Task moved to ``core.task`` in Brain V2."""
from core.task import Task, TaskStatus

__all__ = ["Task", "TaskStatus"]
