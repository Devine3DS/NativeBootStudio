# Build from source

Use **64-bit Windows and Python 3.13.7** for the Windows executable. Commands below run from the repository root in PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe src/studio.py
```

Pillow is the application dependency. PyInstaller builds the executable, Capstone supports instruction-level integration checks, and Black formats the source. No Xbox SDK is required.

## Test and package

```powershell
.\.venv\Scripts\python.exe -m black --check src tests scripts
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/build_release.py --build
```

The packager writes these files to `dist/`:

- `NativeBootStudio-4.2.2-Windows-x64.zip`: EXE, English/German user and installation guides, CRC-32 helper, and license notices.
- `NativeBootStudio-4.2.2-source.zip`: clean source, tests, documentation, build script, and GitHub workflow.
- `SHA256SUMS.txt`: SHA-256 checksums of both archives.

Temporary build output lives in `.build/`. Both folders are ignored by Git. Source packaging uses explicit file/folder allowlists; binaries, Xbox files, personal settings, projects, presets, and private fixtures are excluded. Inspect archive contents before publishing.

To package an already built executable, use `python scripts/build_release.py --exe PATH`. `--out PATH` selects the output folder.

## Optional integration tests

The public repository has no Xbox files or third-party executables. Tests needing an original XEX and XexTool skip when those inputs are absent; all other tests still run. To run the complete integration suite, supply your own files **outside the repository**:

```powershell
$env:NBS_BOOTANIM = 'C:\MyPrivateFiles\bootanim.xex'
$env:NBS_XEXTOOL = 'C:\MyPrivateTools\xextool.exe'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The source must be the supported unmodified modern 17559 original. `NBS_XENIA` optionally points to your own emulator for manual native-preview checks. The application also supports selecting these paths in its Files tab.

GitHub Actions checks formatting, runs the public suite, builds on Windows, and uploads artifacts. It does **not** publish a GitHub release. Hardware boot behavior still requires console verification.

## Dependency notices

The checked-in runtime notices match Python 3.13, Pillow 11.3.0, PyInstaller 6.20.0, and packaging 26.2 used for this release. When changing runtime dependencies, update their notices in `licenses/runtime/` and check the final frozen executable's contents. Xenia, XexTool, and Microsoft binaries are never added by the build script. See [distribution notes](DISTRIBUTION.en.md).
