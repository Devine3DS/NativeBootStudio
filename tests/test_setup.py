import json
from pathlib import Path
import queue
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import i18n


class SetupTests(unittest.TestCase):
    def test_preferences_merge_language_and_external_paths_atomically(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("i18n.app_dir", return_value=Path(directory)),
        ):
            i18n.save_preferences(
                source="C:/My console/original.xex", xextool="C:/My tools/xextool.exe"
            )
            locale = i18n.Locale()
            locale.set("de")
            self.assertEqual(i18n.load_preferences()["source"], "C:/My console/original.xex")
            i18n.save_preferences(xenia="C:/My tools/xenia.exe")
            self.assertEqual(i18n.load_preferences()["language"], "de")
            self.assertEqual(len(list(Path(directory).iterdir())), 1)
            (Path(directory) / "settings.json").write_text(
                json.dumps({"language": {}, "xenia": None})
            )
            self.assertEqual(i18n.load_preferences(), {})

    def test_first_run_without_proprietary_files_is_usable_and_has_no_error_popup(self):
        import tkinter as tk
        import studio

        i18n.locale.set("en", persist=False)
        root = tk.Tk()
        root.withdraw()
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        with (
            tempfile.TemporaryDirectory() as folder,
            patch("studio.load_preferences", return_value={}),
            patch.dict(
                "os.environ",
                {
                    "NBS_BOOTANIM": str(Path(folder) / "absent.xex"),
                    "NBS_XEXTOOL": str(Path(folder) / "absent.exe"),
                    "NBS_XENIA": str(Path(folder) / "absent-xenia.exe"),
                },
            ),
        ):
            app = studio.Studio(root)
            try:
                with patch("tkinter.messagebox.showerror") as popup:
                    app.start_load()
                    root.update()
                    app.poll()
                    self.assertFalse(app.loading)
                    self.assertIsNone(app.verified_identity)
                    self.assertEqual(app.notebook.index(app.notebook.select()), 3)
                    self.assertEqual(str(app.export_button["state"]), "disabled")
                    self.assertFalse(app.gpu.available)
                    popup.assert_not_called()
                    app.preset("black_blue")
                    self.assertEqual(app.profile["background_color"], [0, 0, 0])
                    app.language.set("Deutsch")
                    app.change_language()
                    root.update()
                    self.assertFalse(errors, errors)
            finally:
                app.closed = True
                app.gpu.close()
                try:
                    app.render_jobs.get_nowait()
                except queue.Empty:
                    pass
                app.render_jobs.put_nowait(None)
                for callback in root.tk.call("after", "info"):
                    root.after_cancel(callback)
                root.destroy()
                i18n.locale.set("en", persist=False)
