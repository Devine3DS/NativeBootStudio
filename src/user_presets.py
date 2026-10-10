"""Portable, validated color palettes. Names never become filesystem paths."""

import copy
import json
import os
from pathlib import Path
import tempfile
import uuid

from editor_model import COLOR_KEYS
from native_extension import defaults, validate
from i18n import app_dir

FORMAT = "nativebootstudio.palette"


def checked(value):
    if not isinstance(value, dict) or value.get("format") != FORMAT or value.get("version") != 1:
        raise ValueError("Die Datei enthält kein unterstütztes Farb-Preset.")
    name = value.get("name")
    if (
        not isinstance(name, str)
        or not 1 <= len(name.strip()) <= 64
        or any(ord(c) < 32 for c in name)
    ):
        raise ValueError("Der Name muss 1 bis 64 Zeichen enthalten.")
    colors = value.get("colors")
    if not isinstance(colors, dict) or set(colors) != set(COLOR_KEYS):
        raise ValueError("Das Farb-Preset ist unvollständig.")
    profile = defaults()
    profile.update(copy.deepcopy(colors))
    try:
        profile = validate(profile)
    except (TypeError, KeyError, IndexError, OverflowError) as exc:
        raise ValueError("Das Farb-Preset enthält ungültige Werte.") from exc
    return {
        "format": FORMAT,
        "version": 1,
        "name": name.strip(),
        "colors": {key: copy.deepcopy(profile[key]) for key in COLOR_KEYS},
    }


def from_profile(name, profile):
    profile = validate(profile)
    return checked(
        {
            "format": FORMAT,
            "version": 1,
            "name": name,
            "colors": {key: profile[key] for key in COLOR_KEYS},
        }
    )


def apply(profile, record):
    profile = validate(profile)
    profile.update(checked(record)["colors"])
    return validate(profile)


def read(path):
    path = Path(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Die Preset-Datei ist ungewöhnlich groß.")
    try:
        return checked(json.loads(path.read_text(encoding="utf-8-sig")))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("Die Datei enthält kein lesbares Farb-Preset.") from exc


def atomic_write(path, record):
    record = checked(record)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(record, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


class Store:
    def __init__(self, folder=None):
        self.folder = Path(folder) if folder is not None else app_dir() / "UserPresets"

    def path(self, identity):
        if (
            not isinstance(identity, str)
            or len(identity) != 32
            or any(c not in "0123456789abcdef" for c in identity)
        ):
            raise ValueError("Ungültige Preset-ID.")
        return self.folder / (identity + ".json")

    def list(self):
        records = {}
        errors = []
        for path in sorted(self.folder.glob("*.json")):
            try:
                self.path(path.stem)
                records[path.stem] = read(path)
            except (OSError, ValueError) as exc:
                errors.append((path.name, str(exc)))
        return dict(sorted(records.items(), key=lambda item: item[1]["name"].casefold())), errors

    def save(self, record, identity=None):
        record = checked(record)
        records, _ = self.list()
        if identity is not None and identity not in records:
            raise ValueError("Das Preset wurde nicht gefunden.")
        if any(
            item["name"].casefold() == record["name"].casefold()
            for key, item in records.items()
            if key != identity
        ):
            raise ValueError("Ein Preset mit diesem Namen existiert bereits.")
        identity = identity or uuid.uuid4().hex
        atomic_write(self.path(identity), record)
        return identity

    def rename(self, identity, name):
        record = read(self.path(identity))
        record["name"] = name
        return self.save(record, identity)

    def delete(self, identity):
        self.path(identity).unlink()

    def import_file(self, path):
        return self.save(read(path))

    def export_file(self, identity, path):
        path = Path(path).resolve()
        if path.suffix.lower() != ".json" or path.is_relative_to(self.folder.resolve()):
            raise ValueError("Bitte außerhalb der Preset-Bibliothek als .nbpalette.json speichern.")
        atomic_write(path, read(self.path(identity)))
