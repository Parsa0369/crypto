# Native C++ indicator module

This directory contains an optional C++17 RSI(14) implementation. It is not yet called by the Python dashboard; the current dashboard computes RSI in Python. Keeping this module separate avoids claiming native acceleration before integration and benchmarks exist.

Build with CMake:
```powershell
cmake -S native -B build
cmake --build build --config Release
```
