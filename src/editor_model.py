"""Validated project IO and reversible editing, independent of the UI."""

import colorsys
import copy
import json
import os
from pathlib import Path
import tempfile
import time
from native_extension import defaults, profile_preset, validate
from i18n import app_dir

TARGET_LABELS = {"HDD · interne Festplatte": "hdd", "NAND · Flash-Abbild": "flash"}
COLOR_KEYS = (
    "effects",
    "materials",
    "text_colors",
    "shader_colors",
    "texture_tint",
    "ribbon_tint",
    "background_color",
)


def parse_hex(value):
    value = value.strip().removeprefix("#")
    if len(value) != 6 or any(c not in "0123456789abcdefABCDEF" for c in value):
        raise ValueError("Bitte eine Farbe als #RRGGBB eingeben, z. B. #0080FF.")
    return [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]


def themed(profile, rgb):
    """Change native color groups while retaining text transform and timing."""
    checked = validate(profile)
    hue, saturation, value = colorsys.rgb_to_hsv(*rgb)
    original = defaults()
    for key in ("effects", "shader_colors"):
        checked[key] = [
            list(
                colorsys.hsv_to_rgb(
                    hue, colorsys.rgb_to_hsv(*c)[1] * saturation, colorsys.rgb_to_hsv(*c)[2] * value
                )
            )
            for c in original[key]
        ]
    checked["text_colors"][0] = list(checked["effects"][0])
    checked["texture_tint"] = list(colorsys.hsv_to_rgb(hue, saturation, value))
    checked["ribbon_tint"] = list(checked["texture_tint"])
    return validate(checked)


def apply_preset(profile, name, effects):
    result = validate(profile)
    palette = profile_preset(name, effects)
    for key in COLOR_KEYS:
        result[key] = copy.deepcopy(palette[key])
    return validate(result)


def validate_project(value):
    try:
        if not isinstance(value, dict):
            raise ValueError("Das Projekt muss ein JSON-Objekt enthalten.")
        target = value["target"]
        if target == "nand":
            target = "flash"
        if target not in ("hdd", "flash"):
            raise ValueError("Das Ausgabeziel ist ungültig.")
        for key in ("source", "xextool"):
            if not isinstance(value[key], str) or not value[key].strip():
                raise ValueError("Eingabedatei oder XexTool-Pfad fehlt im Projekt.")
        animation = value.get(
            "animation", "classic" if Path(value["source"]).parent.name == "classic" else "modern"
        )
        if (
            animation != "modern"
            or Path(value["source"]).parent.name == "classic"
            or value["source"].startswith("@bundled:/originals/classic/")
        ):
            raise ValueError("Die klassische Bootanimation wird nicht mehr unterstützt.")
        paths = {
            key: (
                str(app_dir() / value[key][10:])
                if value[key].startswith("@bundled:/")
                else value[key]
            )
            for key in ("source", "xextool")
        }
        for key in ("source", "xextool"):
            if value[key].startswith("@bundled:/") and value[key][10:] not in (
                "originals/modern/bootanim.xex",
                "tools/xextool.exe",
            ):
                raise ValueError("Unbekannter Paketpfad im Projekt.")
        return {
            "profile": validate(value["profile"]),
            **paths,
            "target": target,
            "animation": animation,
        }
    except (KeyError, IndexError, TypeError, AttributeError, OverflowError) as exc:
        raise ValueError("Das Projekt ist unvollständig oder enthält ungültige Werte.") from exc


def project(profile, source, tool, target):
    return validate_project(
        {
            "profile": profile,
            "source": str(Path(source).resolve()),
            "xextool": str(Path(tool).resolve()),
            "target": target,
        }
    )


def read_project(path):
    path = Path(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Die Projektdatei ist ungewöhnlich groß.")
    try:
        return validate_project(json.loads(path.read_text(encoding="utf-8-sig")))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("Die Datei enthält kein lesbares Boot-Studio-Projekt.") from exc


def save_project(path, value):
    checked = validate_project(value)
    path = Path(path).resolve()
    if path in (
        Path(checked["source"]).resolve(),
        Path(checked["xextool"]).resolve(),
        app_dir() / "originals" / "modern" / "bootanim.xex",
    ):
        raise ValueError("Ein Projekt darf weder die Original-XEX noch XexTool überschreiben.")
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = copy.deepcopy(checked)
    for key in ("source", "xextool"):
        try:
            serialized[key] = (
                "@bundled:/" + Path(checked[key]).resolve().relative_to(app_dir()).as_posix()
            )
        except ValueError:
            pass
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
            temporary = Path(f.name)
            json.dump(serialized, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


class History:
    def __init__(self, profile):
        self.profile = validate(profile)
        self.undo_stack = []
        self.redo_stack = []
        self.last_key = None
        self.last_time = 0.0

    def replace(self, value, key=None):
        value = validate(value)
        if value == self.profile:
            return False
        now = time.monotonic()
        if key is None or key != self.last_key or now - self.last_time > 0.5:
            self.undo_stack.append(copy.deepcopy(self.profile))
            self.undo_stack = self.undo_stack[-64:]
        self.profile = value
        self.redo_stack.clear()
        self.last_key = key
        self.last_time = now
        return True

    def undo(self):
        if not self.undo_stack:
            return False
        self.redo_stack.append(self.profile)
        self.profile = self.undo_stack.pop()
        self.last_key = None
        return True

    def redo(self):
        if not self.redo_stack:
            return False
        self.undo_stack.append(self.profile)
        self.profile = self.redo_stack.pop()
        self.last_key = None
        return True
