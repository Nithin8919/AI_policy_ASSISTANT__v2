"""Minimal numpy stub to unblock environments without native numpy."""

from __future__ import annotations

import builtins
import math
import random
import sys
import types
from typing import Iterable, Sequence, Union


def install_numpy_stub() -> None:
    """Install a lightweight numpy replacement into sys.modules."""

    if "numpy" in sys.modules:
        return  # Already installed

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

    def any_(iterable):  # type: ignore
        return builtins.any(iterable)

    class _RandomGenerator:
        def __init__(self, seed=None):
            self._rng = random.Random(seed)

        def standard_normal(self, size):
            return [self._rng.gauss(0, 1) for _ in range(size)]

    class _RandomModule:
        def default_rng(self, seed=None):
            return _RandomGenerator(seed)

    class _LinalgModule:
        def norm(self, vec: Union[ndarray, Sequence[float]]):
            data = vec.tolist() if isinstance(vec, ndarray) else vec
            return math.sqrt(sum(float(x) * float(x) for x in data))

    numpy_mod = types.ModuleType("numpy")
    numpy_mod.ndarray = ndarray
    numpy_mod.array = array
    numpy_mod.asarray = asarray
    numpy_mod.dot = dot
    numpy_mod.mean = mean
    numpy_mod.isfinite = isfinite
    numpy_mod.isnan = isnan
    numpy_mod.any = any_
    numpy_mod.random = _RandomModule()
    numpy_mod.linalg = _LinalgModule()
    numpy_mod.float32 = float
    numpy_mod.float64 = float
    numpy_mod.float16 = float
    numpy_mod.float_ = float
    numpy_mod.int64 = int
    numpy_mod.int32 = int
    numpy_mod.int16 = int
    numpy_mod.int8 = int
    numpy_mod.intp = int
    numpy_mod.uint64 = int
    numpy_mod.uint32 = int
    numpy_mod.uint16 = int
    numpy_mod.uint8 = int
    numpy_mod.uintp = int
    numpy_mod.bool_ = bool
    numpy_mod.bool8 = bool
    numpy_mod.longdouble = float
    numpy_mod.__version__ = "0.0.0-stub"

    sys.modules["numpy"] = numpy_mod

    typing_module = types.ModuleType("numpy.typing")
    typing_module.NDArray = ndarray
    typing_module.ArrayLike = Sequence[float]
    sys.modules["numpy.typing"] = typing_module
