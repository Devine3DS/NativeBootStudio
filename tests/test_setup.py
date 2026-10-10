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
                    for variable in (app.source_display, app.tool_display, app.xenia_display):
                        self.assertEqual(variable.get(), "No file selected")
                    popup.assert_not_called()
                    app.preset("black_blue")
                    self.assertEqual(app.profile["background_color"], [0, 0, 0])
                    app.language.set("Deutsch")
                    app.change_language()
                    root.update()
                    self.assertEqual(app.source_display.get(), "Keine Datei ausgewählt")
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

    def test_setup_displays_only_filenames_and_preserves_real_file_selections(self):
        import tkinter as tk
        import studio

        i18n.locale.set("en", persist=False)
        root = tk.Tk()
        root.withdraw()
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / "ExampleUser" / "Desktop" / "Console tools"
            private.mkdir(parents=True)
            files = [private / name for name in ("bootanim.xex", "xextool.exe", "xenia.exe")]
            for path in files:
                path.write_bytes(b"test fixture; never execute")
            with (
                patch("studio.load_preferences", return_value={}),
                patch.dict(
                    "os.environ",
                    dict(zip(("NBS_BOOTANIM", "NBS_XEXTOOL", "NBS_XENIA"), map(str, files))),
                ),
            ):
                app = studio.Studio(root)
                try:
                    self.assertEqual(
                        [v.get() for v in (app.source, app.tool, app.xenia)], list(map(str, files))
                    )
                    self.assertEqual(
                        [
                            v.get()
                            for v in (app.source_display, app.tool_display, app.xenia_display)
                        ],
                        [p.name for p in files],
                    )

                    def entries(widget):
                        for child in widget.winfo_children():
                            if child.winfo_class() == "TEntry":
                                yield child
                            yield from entries(child)

                    fields = list(entries(app.notebook.nametowidget(app.notebook.tabs()[3])))
                    self.assertEqual(len(fields), 3)
                    self.assertTrue(all(str(field["state"]) == "readonly" for field in fields))
                    self.assertTrue(all("ExampleUser" not in field.get() for field in fields))
                    replacement = private / "Open.xex"
                    replacement.write_bytes(b"another fixture")
                    with (
                        patch("tkinter.filedialog.askopenfilename", return_value=str(replacement)),
                        patch.object(app, "start_load") as load,
                    ):
                        app.browse(app.source, [("Xbox-XEX", "*.xex")])
                        load.assert_called_once()
                    self.assertEqual(app.source.get(), str(replacement))
                    self.assertEqual(app.source_display.get(), "Open.xex")
                    app.language.set("Deutsch")
                    app.change_language()
                    self.assertEqual(app.source_display.get(), "Open.xex")
                    self.assertEqual(app.document()["source"], str(replacement))
                    error = app.display_error(
                        "Cannot read "
                        + str(replacement)
                        + r"; temporary file C:\Users\ExampleUser\AppData\Local\Temp\input.xex"
                    )
                    self.assertNotIn("ExampleUser", error)
                    self.assertNotIn(str(private), error)
                    self.assertIn("Open.xex", error)
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
