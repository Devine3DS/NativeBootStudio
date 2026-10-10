import copy
import json
from pathlib import Path
import queue
import struct
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import animations
import editor_model
import native_boot_color as backend
from native_extension import defaults
from i18n import locale, t, app_dir


class PortableTests(unittest.TestCase):
    def test_language_preference_persists_and_invalid_preference_defaults_to_english(self):
        from unittest.mock import patch
        from i18n import Locale

        with (
            tempfile.TemporaryDirectory() as directory,
            patch("i18n.app_dir", return_value=Path(directory)),
        ):
            selected = Locale()
            self.assertEqual(selected.language, "en")
            selected.set("de")
            self.assertEqual(Locale().language, "de")
            (Path(directory) / "settings.json").write_text("{broken")
            self.assertEqual(Locale().language, "en")

    def test_classic_sources_and_projects_rejected(self):
        with self.assertRaises(ValueError):
            animations.source("classic")
        p = editor_model.project(defaults(), animations.source(), backend.find_tool(), "hdd")
        for source in (
            "@bundled:/originals/classic/bootanim.xex",
            "C:/originals/classic/bootanim.xex",
        ):
            p["source"] = source
            with self.assertRaises(ValueError):
                editor_model.validate_project(p)
        p["source"] = str(animations.source())
        p["animation"] = "classic"
        with self.assertRaises(ValueError):
            editor_model.validate_project(p)
        self.assertFalse((app_dir() / "originals" / "classic").exists())

    def test_bundled_project_paths_portable_and_legacy_paths_preserved(self):
        p = editor_model.project(
            defaults(), animations.source("modern"), app_dir() / "tools/xextool.exe", "hdd"
        )
        with tempfile.TemporaryDirectory() as directory:
            saved = Path(directory) / "portable.json"
            editor_model.save_project(saved, p)
            actual = json.loads(saved.read_text())
            self.assertEqual(actual["source"], "@bundled:/originals/modern/bootanim.xex")
            self.assertEqual(actual["xextool"], "@bundled:/tools/xextool.exe")
            self.assertEqual(actual["animation"], "modern")
            self.assertEqual(editor_model.read_project(saved), p)
            actual["source"] = "@bundled:/../../some-file.xex"
            with self.assertRaises(ValueError):
                editor_model.validate_project(actual)
        old = {
            "profile": defaults(),
            "source": "C:/Other/bootanim.xex",
            "xextool": "C:/Other/xextool.exe",
            "target": "hdd",
        }
        checked = editor_model.validate_project(old)
        self.assertEqual(checked["animation"], "modern")
        self.assertEqual(checked["source"], old["source"])

    def test_bilingual_values_and_palette_names_roundtrip(self):
        import palettes

        locale.set("en", persist=False)
        for phrase in [
            "Alle",
            "Dunkel",
            "Neu · Wirbel",
            *editor_model.TARGET_LABELS,
            *[p[1] for p in palettes.PALETTES],
        ]:
            self.assertEqual(locale.canonical(t(phrase)), phrase)
        self.assertEqual(t("Öffnen"), "Open")
        self.assertEqual(t("Tempo"), "Speed")
        self.assertEqual(locale.canonical("All"), "Alle")
        self.assertEqual(locale.canonical("Alle"), "Alle")
        locale.set("de", persist=False)
        self.assertEqual(t("Open"), "Öffnen")
        caption = "Presets stimmen Hintergrund, Wirbel, Effekte, Kugel\nund Schriftfarben aufeinander ab. Größe und Tempo bleiben."
        german = t(caption)
        for _ in range(3):
            locale.set("en", persist=False)
            english = t(german)
            self.assertEqual(english, t(caption))
            self.assertTrue(english.startswith("Presets coordinate"))
            locale.set("de", persist=False)
            self.assertEqual(t(english), german)
        locale.set("en", persist=False)

    @unittest.skipUnless(
        backend.DEFAULT_INPUT.is_file() and backend.find_tool().is_file(),
        "Native inputs not provided",
    )
    def test_language_switch_keeps_edits_and_only_modern_controls(self):
        import tkinter as tk
        import studio

        locale.set("en", persist=False)
        root = tk.Tk()
        root.withdraw()
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        app = studio.Studio(root)

        def until_ready():
            deadline = time.monotonic() + 12
            while app.verified_identity is None and time.monotonic() < deadline:
                root.update()
                time.sleep(0.005)
            self.assertEqual(
                app.verified_identity, (app.source.get(), app.tool.get()), app.source_status.get()
            )

        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        try:
            app.start_load()
            until_ready()
            app.preset("black_blue")
            app.slider_changed(("text_transform", "scale"), ".83")
            modern = copy.deepcopy(app.profile)
            identity = app.verified_identity
            locale.set("de", root, persist=False)
            app.refresh()
            root.update()
            self.assertEqual(app.profile, modern)
            self.assertEqual(app.verified_identity, identity)
            self.assertEqual(app.export_button["text"], "bootanim.xex exportieren …")
            locale.set("en", root, persist=False)
            app.refresh()
            root.update()
            self.assertEqual(app.export_button["text"], "Export bootanim.xex …")
            self.assertEqual(app.profile, modern)
            self.assertEqual(app.verified_identity, identity)
            # English color dialog uses translated labels and error messages.
            app.choose_color("Abgestimmter Farbton", None)
            dialog = next(c for c in root.winfo_children() if isinstance(c, tk.Toplevel))
            cancel = next(
                c
                for c in descendants(dialog)
                if c.winfo_class() == "TButton" and c["text"] == "Cancel"
            )
            cancel.invoke()
            self.assertEqual(app.profile, modern)
            self.assertFalse(hasattr(app, "animation_box"))
            self.assertEqual(app.metadata["animation"], "modern")
            self.assertTrue(all(app.notebook.tab(i, "state") == "normal" for i in range(4)))
            self.assertFalse(errors, errors)
        finally:
            app.closed = True
            try:
                app.render_jobs.get_nowait()
            except queue.Empty:
                pass
            app.render_jobs.put_nowait(None)
            for callback in root.tk.call("after", "info"):
                root.after_cancel(callback)
            root.destroy()
            locale.set("en", persist=False)


if __name__ == "__main__":
    unittest.main()
