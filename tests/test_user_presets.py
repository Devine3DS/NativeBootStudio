import copy
import json
from pathlib import Path
import queue
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import user_presets as presets
import palettes
from editor_model import COLOR_KEYS
from i18n import locale, t


class PresetTests(unittest.TestCase):
    def test_crud_restart_and_safe_names(self):
        with tempfile.TemporaryDirectory() as folder:
            store = presets.Store(folder)
            record = presets.from_profile("../Blau / Gold · 蓝色", palettes.palette("black_blue"))
            identity = store.save(record)
            self.assertEqual(presets.Store(folder).list()[0][identity], record)
            self.assertEqual(store.path(identity).parent, Path(folder))
            self.assertEqual(len(list(Path(folder).iterdir())), 1)
            store.rename(identity, "Blue")
            self.assertEqual(store.list()[0][identity]["name"], "Blue")
            store.save(presets.from_profile("Blue", palettes.palette("black_gold")), identity)
            self.assertEqual(
                store.list()[0][identity]["colors"]["ribbon_tint"],
                palettes.palette("black_gold")["ribbon_tint"],
            )
            with self.assertRaises(ValueError):
                store.save(presets.from_profile(" blue ", palettes.palette("blue")))
            with self.assertRaises(ValueError):
                store.delete("../file")
            store.delete(identity)
            self.assertEqual(store.list()[0], {})

    def test_apply_is_reversible_and_preserves_layout_and_speed(self):
        from editor_model import History

        before = palettes.palette("midnight")
        before["animation_speed"] = 1.14
        before["text_transform"] = {"scale": 0.84, "x": 0.11, "y": -0.06}
        record = presets.from_profile("My colors", palettes.palette("black_gold"))
        history = History(before)
        history.replace(presets.apply(before, record))
        self.assertEqual(history.profile["text_transform"], before["text_transform"])
        self.assertEqual(history.profile["animation_speed"], 1.14)
        for key in COLOR_KEYS:
            self.assertEqual(history.profile[key], record["colors"][key])
        self.assertEqual(
            before["background_color"], palettes.palette("midnight")["background_color"]
        )
        history.undo()
        self.assertEqual(history.profile, before)

    def test_invalid_imports_skipped_without_hiding_valid_presets(self):
        record = presets.from_profile("Valid", palettes.palette("blue"))
        invalid = []
        for name, value in [("format", "other"), ("version", 99), ("name", "\n")]:
            bad = copy.deepcopy(record)
            bad[name] = value
            invalid.append(bad)
        bad = copy.deepcopy(record)
        del bad["colors"]["effects"]
        invalid.append(bad)
        bad = copy.deepcopy(record)
        bad["colors"]["effects"][0][0] = float("nan")
        invalid.append(bad)
        bad = copy.deepcopy(record)
        bad["colors"]["materials"] = None
        invalid.append(bad)
        for bad in invalid:
            with self.assertRaises(ValueError):
                presets.checked(bad)
        with tempfile.TemporaryDirectory() as folder:
            store = presets.Store(folder)
            identity = store.save(record)
            (Path(folder) / ("0" * 32 + ".json")).write_text("{bad")
            records, errors = store.list()
            self.assertEqual(list(records), [identity])
            self.assertEqual(len(errors), 1)

    def test_sharing_is_portable_and_original_files_are_protected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = presets.Store(root / "One")
            other = presets.Store(root / "Two")
            record = presets.from_profile("Shared", palettes.palette("arctic"))
            identity = store.save(record)
            exported = root / "shared.nbpalette.json"
            store.export_file(identity, exported)
            imported = other.import_file(exported)
            self.assertEqual(other.list()[0][imported], record)
            for path in [root / "bootanim.xex", root / "xextool.exe", store.path(identity)]:
                with self.assertRaises(ValueError):
                    store.export_file(identity, path)
            with self.assertRaises(ValueError):
                other.import_file(exported)
            self.assertEqual(len(other.list()[0]), 1)

    def test_write_failure_preserves_saved_palette(self):
        with tempfile.TemporaryDirectory() as folder:
            store = presets.Store(folder)
            record = presets.from_profile("Safe", palettes.palette("blue"))
            identity = store.save(record)
            with patch("user_presets.os.replace", side_effect=OSError("disk unavailable")):
                with self.assertRaises(OSError):
                    store.rename(identity, "Changed")
            self.assertEqual(store.list()[0][identity], record)
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_library_dialog_language_sharing_replace_delete_and_undo(self):
        import tkinter as tk
        import studio

        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        def click(widget, text):
            next(
                c
                for c in descendants(widget)
                if c.winfo_class() == "TButton" and c["text"] == t(text)
            ).invoke()

        locale.set("en", persist=False)
        root = tk.Tk()
        root.withdraw()
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        with tempfile.TemporaryDirectory() as folder:
            store = presets.Store(Path(folder) / "UserPresets")
            with patch("studio.user_presets.Store", return_value=store):
                app = studio.Studio(root)
            try:
                app.preset("black_blue")
                app.save_user_preset()
                root.update()
                dialog = next(c for c in root.winfo_children() if isinstance(c, tk.Toplevel))
                entry = next(c for c in descendants(dialog) if c.winfo_class() == "TEntry")
                entry.insert(0, "Blue / Gold · Grüß")
                click(dialog, "Speichern")
                root.update()
                identity = next(iter(app.user_records))
                app.show_library()
                root.update()
                app.library_tree.selection_set(identity)
                self.assertEqual(app.library_tree.item(identity, "values")[0], "Blue / Gold · Grüß")
                for language in ("de", "en"):
                    app.language.set("Deutsch" if language == "de" else "English")
                    app.change_language()
                    root.update()
                    self.assertEqual(
                        app.library_tree.item(identity, "values")[0], "Blue / Gold · Grüß"
                    )
                self.assertEqual(
                    app.preset_hint_text.get(), t("Eigenes Preset: ") + "Blue / Gold · Grüß"
                )
                app.preset("black_gold")
                app.slider_changed(("animation_speed",), "1.14")
                before = copy.deepcopy(app.profile)
                app.apply_user_preset(identity)
                self.assertEqual(app.profile["animation_speed"], 1.14)
                self.assertEqual(
                    app.profile["ribbon_tint"], palettes.palette("black_blue")["ribbon_tint"]
                )
                app.undo()
                self.assertEqual(app.profile, before)
                app.show_library()
                app.library_tree.selection_set(identity)
                root.update()
                exported = Path(folder) / "shared.nbpalette.json"
                with patch("tkinter.filedialog.asksaveasfilename", return_value=str(exported)):
                    app.export_user_preset()
                with patch("tkinter.messagebox.askyesno", return_value=True):
                    app.replace_user_preset()
                self.assertEqual(
                    app.user_records[identity]["colors"]["ribbon_tint"],
                    palettes.palette("black_gold")["ribbon_tint"],
                )
                with patch("tkinter.messagebox.askyesno", return_value=True):
                    app.delete_user_preset()
                self.assertEqual(app.user_records, {})
                with patch("tkinter.filedialog.askopenfilename", return_value=str(exported)):
                    app.import_user_preset()
                self.assertEqual(len(app.user_records), 1)
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
                locale.set("en", persist=False)
