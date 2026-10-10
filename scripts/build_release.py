"""Build public archives from explicit allowlists; never include external assets."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.search(
    r'VERSION\s*=\s*[\'"]([^\'"]+)', (ROOT / "src/studio.py").read_text(encoding="utf-8")
).group(1)
SOURCE_DIRS = ("src", "tests", "scripts", "docs", "licenses", ".github")
SOURCE_FILES = (
    "README.md",
    "README.de.md",
    "LICENSE",
    "NOTICE.md",
    "CHANGELOG.md",
    ".gitignore",
    ".gitattributes",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "GPU-Preview-Implementation.md",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files():
    files = [ROOT / name for name in SOURCE_FILES]
    for folder in SOURCE_DIRS:
        files.extend(
            path
            for path in (ROOT / folder).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and allowed_source(path, folder)
        )
    assert all(file.is_file() for file in files)
    return sorted(files)


def allowed_source(path, folder):
    if path.is_symlink():
        return False
    suffixes = {
        "src": (".py",),
        "tests": (".py",),
        "scripts": (".py", ".ps1"),
        "docs": (".md", ".png"),
        ".github": (".yml", ".yaml"),
    }
    if folder in suffixes:
        return path.suffix.lower() in suffixes[folder]
    return path.name in (
        "Pillow-LICENSE.txt",
        "PyInstaller-COPYING.txt",
        "Python-LICENSE.txt",
        "Tcl-license.terms",
        "Tk-license.terms",
        "LICENSE",
        "LICENSE.APACHE",
        "LICENSE.BSD",
    )


def archive(output, entries):
    for _, name in entries:
        lower = name.lower()
        if (
            lower.endswith((".xex", ".image", ".bin", ".pyc", ".pyo", ".dll"))
            or "xextool.exe" in lower
            or "xenia.exe" in lower
            or any(
                part in name.split("/") for part in ("work", "__pycache__", ".venv", "UserPresets")
            )
            or lower.endswith("settings.json")
        ):
            raise ValueError(f"Forbidden public archive entry: {name}")
    temporary = output.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as package:
        for path, name in entries:
            package.write(path, name)
    with zipfile.ZipFile(temporary) as package:
        assert package.testzip() is None
        for name in package.namelist():
            assert not name.lower().endswith((".xex", ".image", ".bin", ".pyc"))
            assert "xextool.exe" not in name.lower() and "xenia.exe" not in name.lower()
            assert not any(
                part in name.split("/") for part in ("work", "__pycache__", ".venv", "UserPresets")
            )
            assert not name.endswith("settings.json")
    temporary.replace(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build", action="store_true", help="Compile a Windows EXE using PyInstaller"
    )
    parser.add_argument("--exe", type=Path, help="Use an already compiled EXE")
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.build:
        if sys.platform != "win32":
            parser.error("The Windows release must be built on Windows.")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                "--onefile",
                "--windowed",
                "--name",
                "NativeBootStudio",
                "--exclude-module",
                "numpy",
                "--exclude-module",
                "psutil",
                "--exclude-module",
                "charset_normalizer",
                "--distpath",
                str(ROOT / ".build/bin"),
                "--workpath",
                str(ROOT / ".build/pyinstaller"),
                "--specpath",
                str(ROOT / ".build/spec"),
                str(ROOT / "src/studio.py"),
            ],
            check=True,
            cwd=ROOT,
        )
        executable = ROOT / ".build/bin/NativeBootStudio.exe"
    else:
        executable = args.exe
        if executable is None or not executable.is_file():
            parser.error("Use --build or --exe PATH.")
    prefix = f"NativeBootStudio-{VERSION}"
    release = args.out / f"{prefix}-Windows-x64.zip"
    release_docs = ROOT / ".build/public-docs"
    release_docs.mkdir(parents=True, exist_ok=True)
    for language in ("en", "de"):
        content = (ROOT / f"docs/QUICKSTART.{language}.md").read_text(encoding="utf-8")
        (release_docs / f"QUICKSTART.{language}.md").write_text(
            content.replace("(INSTALLATION.", "(docs/INSTALLATION."), encoding="utf-8"
        )
    entries = [
        (executable, f"{prefix}/NativeBootStudio.exe"),
        (release_docs / "QUICKSTART.en.md", f"{prefix}/README.md"),
        (release_docs / "QUICKSTART.de.md", f"{prefix}/README-DE.md"),
        (ROOT / "LICENSE", f"{prefix}/LICENSE"),
        (ROOT / "NOTICE.md", f"{prefix}/NOTICE.md"),
        (ROOT / "docs/INSTALLATION.en.md", f"{prefix}/docs/INSTALLATION.en.md"),
        (ROOT / "docs/INSTALLATION.de.md", f"{prefix}/docs/INSTALLATION.de.md"),
        (ROOT / "scripts/crc32.ps1", f"{prefix}/scripts/crc32.ps1"),
    ]
    entries.extend(
        (path, f'{prefix}/licenses/{path.relative_to(ROOT/"licenses").as_posix()}')
        for path in (ROOT / "licenses/runtime").rglob("*")
        if path.is_file()
    )
    archive(release, entries)
    source = args.out / f"{prefix}-source.zip"
    archive(
        source,
        [(file, f"{prefix}-source/{file.relative_to(ROOT).as_posix()}") for file in source_files()],
    )
    sums = args.out / "SHA256SUMS.txt"
    sums.write_text(
        "".join(f"{digest(file)}  {file.name}\n" for file in (release, source)), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "version": VERSION,
                "release": str(release),
                "source": str(source),
                "release_sha256": digest(release),
                "source_sha256": digest(source),
                "exe_sha256": digest(executable),
                "runtime_files": len(entries),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
