# Release validation

Validated locally on Windows x64 on **10 October 2026**, using Python 3.13.7 and the pinned build dependencies. Hardware boot behavior is not covered by PC tests.

| Check | Result |
| --- | --- |
| Black formatting | All 20 Python files pass. |
| Public test suite, no Xbox/tool inputs | 46 tests discovered; 24 pass, 22 private-input integration tests skip. |
| Integration suite with user-supplied original/XexTool outside the repository | All 46 tests pass. |
| File-selection privacy | All three setup fields show filenames only; missing-file labels translate; real selections and project loading paths are preserved. |
| Frozen EXE first launch without external files | English and German setup shown; export disabled; no missing-file error popup. |
| Frozen EXE with remembered external paths | Custom preset library works in English and German, including sharing and undo. |
| Shader preview with separately selected Xenia | Original renderer produces frames; no emulator is needed inside the release folder. |
| Frozen HDD and NAND exports | Both round-trip checks pass and output bytes match the previous 4.2 blue/black exports. |
| Original input after all checks | SHA-256 unchanged. |
| CRC-32 helper for NAND INI entries | Standard `123456789` vector and actual exported XEX cross-checked against Python zlib. |
| Public archives | ZIP integrity and file allowlists checked; no XEX, XexTool, Xenia, settings, private projects, presets, or build caches. |

The Windows EXE was compiled in a fresh virtual environment. Its third-party application modules are Pillow and packaging, alongside Python/Tcl/Tk and the PyInstaller bootloader; unrelated locally installed packages are absent. Runtime notices are included.

The previous 4.2.1 GitHub workflow passed. Verify the checks attached to the current commit before using a future CI-produced build.

The shader preview modifies only a temporary PC adapter. It omits normal boot audio/system handoff, and emulator rendering can differ from hardware. Edited timing does not retime audio. Test final console boot behavior and matching-time captures separately. This release supports the modern 17559 source, not the classic animation or custom replacement text.

Installation guides cover the external HDD remap and direct NAND filesystem replacement. Their configuration/command instructions were checked against the upstream release and J-Runner source/package; no console was flashed as part of this validation.

SHA-256 checksums for the final source and Windows archives are distributed separately in `SHA256SUMS.txt` beside the ZIPs.
