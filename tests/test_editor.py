import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import editor_model as model
import native_extension as native
import native_boot_color as backend
import scene


class EditorTests(unittest.TestCase):
    def test_presets_and_coordinated_theme_retain_transform_and_speed(self):
        original = native.defaults()
        original["text_transform"] = {"scale": 0.8, "x": 0.12, "y": -0.1}
        original["animation_speed"] = 1.2
        snapshot = copy.deepcopy(original)
        for name in ("blue", "cyan", "purple", "original"):
            p = model.apply_preset(original, name, backend.preset(name))
            self.assertEqual(p["text_transform"], snapshot["text_transform"])
            self.assertEqual(p["animation_speed"], 1.2)
        p = model.themed(original, [0, 0.5, 1])
        self.assertEqual(p["text_transform"], snapshot["text_transform"])
        self.assertEqual(p["animation_speed"], 1.2)
        self.assertEqual(p["texture_tint"], [0, 0.5, 1])
        self.assertEqual(p["texture_tint"], p["ribbon_tint"])
        self.assertEqual(original, snapshot)
        self.assertTrue(all(rgb[2] > rgb[1] > rgb[0] for _, rgb in scene.native_color_samples(p)))
        dark = model.themed(original, [0, 0.2, 0.4])
        self.assertEqual(dark["ribbon_tint"], [0, 0.2, 0.4])
        self.assertAlmostEqual(max(dark["effects"][0]), max(p["effects"][0]) * 0.4)

    def test_history_coalescing_redo_branch_and_limit(self):
        history = model.History(native.defaults())
        with patch.object(model.time, "monotonic", side_effect=[1.0, 1.1, 1.2, 2.0]):
            for scale in (0.8, 0.7):
                p = copy.deepcopy(history.profile)
                p["text_transform"]["scale"] = scale
                history.replace(p, "scale")
            self.assertEqual(len(history.undo_stack), 1)
            self.assertTrue(history.undo())
            self.assertEqual(history.profile, native.defaults())
            self.assertTrue(history.redo())
            self.assertEqual(history.profile["text_transform"]["scale"], 0.7)
            history.undo()
            p = copy.deepcopy(history.profile)
            p["animation_speed"] = 1.2
            history.replace(p)
            self.assertFalse(history.redo())
        for index in range(80):
            p = copy.deepcopy(history.profile)
            p["animation_speed"] = 1.0 if index % 2 else 1.1
            history.replace(p)
        self.assertEqual(len(history.undo_stack), 64)

    def test_project_validation_and_roundtrip(self):
        p = model.project(native.defaults(), backend.DEFAULT_INPUT, backend.find_tool(), "nand")
        self.assertEqual(p["target"], "flash")
        bad_values = [
            None,
            [],
            {},
            dict(p, target="unknown"),
            dict(p, source=""),
            dict(p, profile=[]),
        ]
        for field, value in [
            ("effects", None),
            ("materials", [None] * 5),
            ("text_transform", {}),
            ("animation_speed", float("nan")),
            ("texture_tint", [True, 0, 1]),
        ]:
            modified = copy.deepcopy(p)
            modified["profile"][field] = value
            bad_values.append(modified)
        for bad in bad_values:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                model.validate_project(bad)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Entwurf.nbstudio.json"
            model.save_project(path, p)
            self.assertEqual(model.read_project(path), p)
            path.write_text("{ broken", encoding="utf-8")
            with self.assertRaises(ValueError):
                model.read_project(path)

    def test_project_failed_save_preserves_previous_and_protects_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "original.xex"
            source.write_bytes(b"original")
            tool = Path(directory) / "xextool.exe"
            tool.write_bytes(b"tool")
            p = model.project(native.defaults(), source, tool, "hdd")
            for path in (source, tool):
                with self.assertRaises(ValueError):
                    model.save_project(path, p)
            target = Path(directory) / "project.json"
            target.write_bytes(b"previous")
            with patch.object(model.os, "replace", side_effect=PermissionError("locked")):
                with self.assertRaises(PermissionError):
                    model.save_project(target, p)
            self.assertEqual(target.read_bytes(), b"previous")
            self.assertEqual(
                sorted(f.name for f in Path(directory).iterdir()),
                ["original.xex", "project.json", "xextool.exe"],
            )

    def test_failed_report_publish_restores_previous_xex_and_removes_new_xex(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "bootanim.xex"
            report = target.with_suffix(".report.json")
            target.write_bytes(b"old xex")
            report.write_bytes(b"old report")
            original_replace = backend.os.replace

            def deny_report(source, destination):
                if Path(destination) == report:
                    raise PermissionError("report locked")
                return original_replace(source, destination)

            with patch.object(backend.os, "replace", side_effect=deny_report):
                with self.assertRaises(PermissionError):
                    backend.publish_export(target, b"new xex", {"new": True})
                self.assertEqual(target.read_bytes(), b"old xex")
                self.assertEqual(report.read_bytes(), b"old report")
                target.unlink()
                with self.assertRaises(PermissionError):
                    backend.publish_export(target, b"new xex", {"new": True})
                self.assertFalse(target.exists())
            self.assertEqual(list(Path(directory).iterdir()), [report])
            backend.publish_export(target, b"new xex", {"new": True})
            self.assertEqual(target.read_bytes(), b"new xex")
            self.assertEqual(json.loads(report.read_text()), {"new": True})

    def test_hex_invalid_values(self):
        self.assertEqual(model.parse_hex("#0080FF"), [0, 128 / 255, 1])
        for invalid in ("#123", "ffffff00", "ffggff", ""):
            with self.assertRaises(ValueError):
                model.parse_hex(invalid)

    @unittest.skipUnless(
        backend.DEFAULT_INPUT.is_file() and backend.find_tool().is_file(),
        "Native inputs not provided",
    )
    def test_both_export_targets_preserve_image_and_match_media_bindings(self):
        p = native.profile_preset("blue", backend.preset("blue"))
        with tempfile.TemporaryDirectory() as directory:
            reports = []
            for target in ("hdd", "flash"):
                reports.append(
                    backend.build(
                        backend.DEFAULT_INPUT,
                        Path(directory) / (target + ".xex"),
                        backend.find_tool(),
                        p["effects"],
                        target,
                        False,
                        p,
                    )
                )
            hdd, nand = reports
            self.assertEqual(hdd["output_image_sha256"], nand["output_image_sha256"])
            self.assertEqual(hdd["allowed_media_after"], "0xffffffff")
            self.assertIsNone(hdd["bounding_path_after"])
            self.assertEqual(nand["allowed_media_before"], nand["allowed_media_after"])
            self.assertEqual(nand["bounding_path_before"], nand["bounding_path_after"])
            self.assertIsNotNone(nand["bounding_path_after"])
            self.assertEqual(
                hdd["output_sha256"],
                "00ac4eece003311f7fd6f6cf1def2264f4e4c7713d304b04922089ebd2e2ac18",
            )


class GUIRegressionTests(unittest.TestCase):
    def setUp(self):
        from i18n import locale

        locale.set("de", persist=False)

    def tearDown(self):
        from i18n import locale

        locale.set("en", persist=False)

    @unittest.skipUnless(
        backend.DEFAULT_INPUT.is_file() and backend.find_tool().is_file(),
        "Native inputs not provided",
    )
    def test_gallery_filter_select_undo_and_close(self):
        import tkinter as tk
        import queue
        import time
        import studio
        import scene
        import palettes
        from test_studio import IMAGE

        root = tk.Tk()
        root.withdraw()
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        app = studio.Studio(root)
        app.scene = scene.extract(IMAGE)
        try:
            initial = copy.deepcopy(app.profile)
            app.preset_group.set("Basis")
            app.filter_presets()
            self.assertEqual(app.profile, initial)
            app.show_gallery()
            root.update()
            self.assertEqual(len(app.gallery_cards), 40)
            box = next(
                child
                for head in app.gallery.winfo_children()
                for child in head.winfo_children()
                if child.winfo_class() == "TCombobox"
            )
            box.set("Dunkel")
            box.event_generate("<<ComboboxSelected>>")
            root.update()
            self.assertEqual(len(app.gallery_cards), 14)
            token = app.gallery_token
            deadline = time.monotonic() + 4
            while (
                not all(hasattr(card, "image") for card in app.gallery_cards.values())
                and time.monotonic() < deadline
            ):
                root.update()
                time.sleep(0.005)
            self.assertTrue(all(hasattr(card, "image") for card in app.gallery_cards.values()))
            app.gallery_cards["black_blue"].event_generate("<Button-1>", x=50, y=50)
            root.update()
            self.assertEqual(app.profile["background_color"], [0, 0, 0])
            self.assertEqual(app.preset_name.get(), palettes.BY_ID["black_blue"][1])
            self.assertEqual(app.preset_group.get(), "Dunkel")
            self.assertIn(app.preset_name.get(), app.preset_box["values"])
            app.undo()
            self.assertIsNone(app.profile["background_color"])
            self.assertEqual(app.preset_group.get(), "Basis")
            self.assertIn(app.preset_name.get(), app.preset_box["values"])
            app.redo()
            app.reset_background()
            self.assertIsNone(app.profile["background_color"])
            app.undo()
            self.assertEqual(app.profile["background_color"], [0, 0, 0])
            app.gallery.destroy()
            app.preset("cyan")
            root.update()
            app.slider_changed(("ribbon_tint", 0), ".123")
            self.assertEqual(app.preset_name.get(), "Eigene Palette")
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

    def test_live_dialog_history_invalid_input_and_stale_loading_results(self):
        import tkinter as tk
        import queue
        import studio

        root = tk.Tk()
        root.withdraw()
        errors = []
        root.report_callback_exception = lambda *args: errors.append(args)
        app = studio.Studio(root)

        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        def dialog():
            return next(c for c in root.winfo_children() if isinstance(c, tk.Toplevel))

        def click(window, label):
            next(
                c
                for c in descendants(window)
                if c.winfo_class() == "TButton" and c["text"] == label
            ).invoke()

        try:
            self.assertFalse(app.dirty())
            initial = copy.deepcopy(app.profile)
            app.choose_color("Live-Farbe", ("ribbon_tint",))
            window = dialog()
            entry = next(c for c in descendants(window) if c.winfo_class() == "TEntry")
            entry.delete(0, "end")
            entry.insert(0, "#EE3300")
            root.update()
            self.assertEqual(app.color_draft["ribbon_tint"], model.parse_hex("#EE3300"))
            self.assertEqual(app.profile, initial)
            click(window, "Abbrechen")
            self.assertEqual(app.profile, initial)
            self.assertIsNone(app.color_draft)
            app.choose_color("Live-Farbe", ("ribbon_tint",))
            window = dialog()
            entry = next(c for c in descendants(window) if c.winfo_class() == "TEntry")
            entry.delete(0, "end")
            entry.insert(0, "invalid")
            root.update()
            apply = next(
                c
                for c in descendants(window)
                if c.winfo_class() == "TButton" and c["text"] == "Übernehmen"
            )
            self.assertEqual(str(apply["state"]), "disabled")
            entry.delete(0, "end")
            entry.insert(0, "#00FFFF")
            root.update()
            apply.invoke()
            self.assertEqual(app.profile["ribbon_tint"], [0, 1, 1])
            self.assertTrue(app.dirty())
            app.undo()
            self.assertEqual(app.profile, initial)
            app.redo()
            app.choose_color("RGB-Eingabe", ("ribbon_tint",))
            window = dialog()
            entries = [c for c in descendants(window) if c.winfo_class() == "TEntry"]
            green = entries[2]
            green.delete(0, "end")
            green.insert(0, "999")
            root.update()
            apply = next(
                c
                for c in descendants(window)
                if c.winfo_class() == "TButton" and c["text"] == "Übernehmen"
            )
            self.assertEqual(str(apply["state"]), "disabled")
            green.delete(0, "end")
            green.insert(0, "128")
            root.update()
            apply.invoke()
            self.assertEqual(app.profile["ribbon_tint"], [0, 128 / 255, 1])
            app.slider_changed(("text_transform", "scale"), ".8")
            app.preset("blue")
            self.assertEqual(app.profile["text_transform"]["scale"], 0.8)
            app.updating = True
            app.target.set(list(model.TARGET_LABELS)[1])
            self.assertTrue(app.updating)
            app.updating = False
            app.loading = True
            app.load_token = 9
            app.source.set("missing.xex")
            self.assertFalse(app.loading)
            self.assertIsNone(app.verified_identity)
            app.events.put(("source", (9, ("old.xex", "tool.exe"), ([], []), {})))
            app.poll()
            self.assertIsNone(app.scene)
            self.assertEqual(str(app.export_button["state"]), "disabled")
            app.events.put(("source-error", (app.load_token, "Fehler-Test")))
            app.poll()
            self.assertIn("Fehler-Test", app.source_status.get())
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


if __name__ == "__main__":
    unittest.main()
