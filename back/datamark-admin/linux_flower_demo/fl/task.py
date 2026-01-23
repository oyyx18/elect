"""Task routing for image classification and object detection."""

from __future__ import annotations

import os
from importlib import import_module
from types import ModuleType

DEFAULT_TASK_TYPE = os.getenv("FLOWER_TASK_TYPE", "classification")

_TASK_ALIASES = {
    "classification": "fl.task_classification",
    "image-classification": "fl.task_classification",
    "cls": "fl.task_classification",
    "detection": "fl.task_detection",
    "object-detection": "fl.task_detection",
    "yolo": "fl.task_detection",
}


def get_task(task_type: str | None = None) -> ModuleType:
    """Return the task module for the requested task type."""

    task_key = (task_type or DEFAULT_TASK_TYPE).strip().lower()
    module_path = _TASK_ALIASES.get(task_key)
    if module_path is None:
        raise ValueError(f"Unknown task type: {task_type}")
    return import_module(module_path)


_default_task = get_task(DEFAULT_TASK_TYPE)

Net = _default_task.Net
load_data = _default_task.load_data
load_centralized_dataset = _default_task.load_centralized_dataset
train = _default_task.train
test = _default_task.test

__all__ = [
    "get_task",
    "Net",
    "load_data",
    "load_centralized_dataset",
    "train",
    "test",
]
