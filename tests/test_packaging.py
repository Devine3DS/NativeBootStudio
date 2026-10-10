import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_packager", ROOT / "scripts/build_release.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class PackagingTests(unittest.TestCase):
    def test_source_allowlist_excludes_private_inputs_and_build_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in packager.SOURCE_FILES:
                (root / name).write_text("public", encoding="utf-8")
            public = [
                "src/editor.py",
                "tests/test_editor.py",
                "scripts/build.py",
                "scripts/crc32.ps1",
                "docs/guide.md",
                "docs/assets/library.png",
                ".github/workflows/build.yml",
                "licenses/runtime/Python-LICENSE.txt",
            ]
            private = [
                "src/.env",
                "src/settings.json",
                "src/original.xex",
                "src/__pycache__/editor.pyc",
                "docs/original.xex",
                "docs/private.nbstudio.json",
                "docs/personal.nbpalette.json",
                "licenses/runtime/unrelated.txt",
                "tools/xextool.exe",
                "dist/application.exe",
            ]
            for name in public + private:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test")
            with patch.object(packager, "ROOT", root):
                actual = {file.relative_to(root).as_posix() for file in packager.source_files()}
            self.assertEqual(actual, set(packager.SOURCE_FILES) | set(public))

    def test_archive_rejects_proprietary_inputs_before_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            dummy = root / "input"
            dummy.write_bytes(b"private")
            for name in (
                "original.xex",
                "tools/xextool.exe",
                "tools/xenia.exe",
                "settings.json",
                "UserPresets/theme.json",
                "nand.bin",
            ):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    packager.archive(root / "release.zip", [(dummy, name)])
                self.assertEqual({file.name for file in root.iterdir()}, {"input"})
