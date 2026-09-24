"""Build hook for the optional native kernels (the package metadata is in pyproject.toml).

``pip install .`` / ``pip install -e .`` compile ``native/resense_native.cpp`` into
``resense/_resense_native*.so`` (a plain C ABI loaded with ctypes by ``resense/_native.py``: no
Python headers or pybind11 needed, only a C++17 compiler). The extension is optional: without a
compiler the build prints a warning, installs the pure-Python package and the detector runs on
numpy alone, with identical results.

The flags keep the floating-point arithmetic bit-identical to numpy: no FMA contraction, no
fast-math, no -march=native (the evaluation machine is not the build machine).
"""
import os

from setuptools import Extension, setup

FLAGS = [] if os.name == "nt" else ["-O3", "-g0", "-std=c++17", "-ffp-contract=off", "-fno-fast-math"]

setup(ext_modules=[Extension("resense._resense_native", sources=["native/resense_native.cpp"],
                             language="c++", extra_compile_args=FLAGS, optional=True)])
