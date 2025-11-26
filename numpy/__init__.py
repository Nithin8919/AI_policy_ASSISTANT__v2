"""Lightweight numpy stub for constrained environments.
Provides just enough surface area for project tests without native deps."""

from __future__ import annotations

import builtins
import math
import random
import sys
import types
from typing import Iterable, Sequence, Union

__all__ = [
    "array",
    "asarray",
    "ndarray",
    "dot",
    "mean",
    "isfinite",
    "isnan",
    "float32",
    "random",
    "linalg",
    "any",
]

__version__ = "0.0.0-stub"
float32 = float
float64 = float
float16 = float
int64 = int
int32 = int
int16 = int
int8 = int
uint64 = int
uint32 = int
uint16 = int
uint8 = int
intp = int
uintp = int
float_ = float
bool_ = bool
bool8 = bool
longdouble = float


class ndarray:
    """Tiny ndarray surrogate backed by a Python list."""

    def __init__(self, data: Union[Sequence[float], Iterable[float]]):
        self._data = [float(x) for x in data]

    def tolist(self):
        return list(self._data)

    def astype(self, _dtype):
        return ndarray(self._data)

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, idx):
        return self._data[idx]

    def __repr__(self):
        return f"ndarray({self._data!r})"

    @classmethod
    def __class_getitem__(cls, _item):
        return cls

def array(data: Union[Sequence[float], Iterable[float]]):
    if isinstance(data, ndarray):
        return ndarray(data.tolist())
    return ndarray(data)


def asarray(data: Union[Sequence[float], Iterable[float]]):
    if isinstance(data, ndarray):
        return data
    return array(data)


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def mean(values: Sequence[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else 0.0


def isfinite(value: float) -> bool:
    return math.isfinite(value)


def isnan(value: float) -> bool:
    return math.isnan(value)


def any(iterable):  # type: ignore[override]
    return builtins.any(iterable)


class _RandomGenerator:
    def __init__(self, seed=None):
        self._rng = random.Random(seed)

    def standard_normal(self, size):
        return [self._rng.gauss(0, 1) for _ in range(size)]


class _RandomModule:
    def default_rng(self, seed=None):
        return _RandomGenerator(seed)


random = _RandomModule()


class _LinalgModule:
    def norm(self, vec: Union[ndarray, Sequence[float]]):
        data = vec.tolist() if isinstance(vec, ndarray) else vec
        return math.sqrt(sum(float(x) * float(x) for x in data))


linalg = _LinalgModule()

# Minimal typing helpers so external packages importing numpy.typing succeed
typing_module = types.ModuleType("numpy.typing")
typing_module.NDArray = ndarray
typing_module.ArrayLike = Sequence[float]
sys.modules["numpy.typing"] = typing_module
