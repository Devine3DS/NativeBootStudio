"""Experimental native palette editor for one verified Xbox 360 bootanim image.

Original editor code: MIT, 2026. External XexTool is not part of this source.
No console writes, video conversion, or NAND generation are performed.
"""

from __future__ import annotations

import colorsys
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from i18n import app_dir

IMAGE_SHA256 = "b2bc842157ea7fbc6fde9adede7d55a5b6b9a4bdb88f73fbdb01f03371b1835b"
DEFAULT_INPUT = Path(
    os.environ.get("NBS_BOOTANIM", app_dir() / "originals" / "modern" / "bootanim.xex")
)
SLOTS = (
    ("Leuchteffekt (Shader)", 0x1424, (0.69, 0.94, 0.22, 1.0)),
    ("Helle Effektschicht", 0x591C8, (0.75, 1.0, 0.75, 1.0)),
    ("Wirbel / Szenenfarbe", 0x59240, (0.05, 0.35, 0.06, 1.0)),
)
ORIGINALS = [struct.unpack(">4f", struct.pack(">4f", *slot[2])) for slot in SLOTS]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def word(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def read_uncompressed(data: bytes) -> tuple[int, bytes]:
    if data[:4] != b"XEX2" or len(data) < 24:
        raise ValueError("Keine gültige XEX2-Datei.")
    payload, security, count = word(data, 8), word(data, 16), word(data, 20)
    if count > 128 or security + 0x184 > len(data):
        raise ValueError("Ungültiger XEX-Header.")
    options = {word(data, 24 + 8 * i): word(data, 28 + 8 * i) for i in range(count)}
    fmt = options.get(0x3FF)
    if fmt is None or fmt + 8 > len(data):
        raise ValueError("XEX-Dateiformat fehlt.")
    encryption, compression = struct.unpack_from(">HH", data, fmt + 4)
    # XexTool's "uncompressed" output uses one basic-compression block,
    # containing the entire image with zero bytes of omitted padding.
    basic_flat = (
        compression == 1
        and word(data, fmt) == 16
        and word(data, fmt + 8) == word(data, security + 4)
        and word(data, fmt + 12) == 0
    )
    if encryption or (compression != 0 and not basic_flat):
        raise ValueError("Interne Prüfung erwartet eine unverschlüsselte, unkomprimierte XEX.")
    size = word(data, security + 4)
    if (
        word(data, 4) != 9
        or size != 0x9C000
        or word(data, security + 0x110) != 0x98000000
        or word(data, security + 0x160) != 0x98058304
        or options.get(0x10201) != 0x98000000
        or payload + size > len(data)
    ):
        raise ValueError(
            "Diese Bootanimation wird nicht unterstützt (erwartet: die untersuchte 17559-DLL)."
        )
    image = data[payload : payload + size]
    normalized = bytearray(image)
    for (_, offset, _), rgba in zip(SLOTS, ORIGINALS):
        struct.pack_into(">4f", normalized, offset, *rgba)
    if sha(normalized) != IMAGE_SHA256:
        raise ValueError(
            "Unbekanntes Programmabbild. Keine passenden Offsets garantiert; Export abgebrochen."
        )
    for _, offset, _ in SLOTS:
        values = struct.unpack_from(">4f", image, offset)
        if any(not math.isfinite(v) or not 0 <= v <= 1 for v in values[:3]) or values[3] != 1:
            raise ValueError("Unerwartete Farb- oder Alphawerte.")
    return payload, image


def preset(name: str) -> list[tuple[float, float, float]]:
    if name == "original":
        return [rgba[:3] for rgba in ORIGINALS]
    hue = {"blue": 2 / 3, "cyan": 1 / 2, "purple": 5 / 6}[name]
    return [colorsys.hsv_to_rgb(hue, *colorsys.rgb_to_hsv(*rgba[:3])[1:]) for rgba in ORIGINALS]


def run_tool(tool: Path, *args: object) -> str:
    result = subprocess.run(
        [str(tool.resolve()), *map(str, args)],
        capture_output=True,
        timeout=90,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    if result.returncode or "Error " in output or "Successfully" not in output:
        raise RuntimeError("XexTool konnte den Arbeitsschritt nicht abschließen:\n" + output)
    return output


def verify_hook_pages(xex):
    """The XEX page descriptors, rather than PE virtual size, govern mapping."""
    sec = word(xex, 16)
    size = 4096 if word(xex, sec + 0x10C) & 0x10000000 else 65536
    offset = 0
    count = word(xex, sec + 0x180)
    if not 1 <= count <= 128 or sec + 0x184 + count * 24 > len(xex):
        raise ValueError("Ungültige XEX-Seitenbeschreibung.")
    covered = set()
    for i in range(count):
        descriptor = word(xex, sec + 0x184 + 24 * i)
        end = offset + (descriptor >> 4) * size
        if descriptor & 15 == 1:
            covered.update(range(max(offset, 0x58340), min(end, 0x59000)))
        offset = end
    if covered != set(range(0x58340, 0x59000)):
        raise ValueError("Der Material-Codebereich ist nicht als ausführbar markiert.")


def media_bindings(data):
    security = word(data, 16)
    count = word(data, 20)
    if count > 128 or 24 + count * 8 > len(data):
        raise ValueError("Ungültige XEX-Headerliste.")
    bounding = None
    for index in range(count):
        key, offset = struct.unpack_from(">II", data, 24 + index * 8)
        if key == 0x80FF:
            size = word(data, offset)
            if size < 4 or offset + size > len(data):
                raise ValueError("Ungültige XEX-Pfadbindung.")
            bounding = bytes(data[offset : offset + size])
    return word(data, security + 0x17C), bounding


def publish_export(target, output_bytes, report):
    """Prepare both artifacts; restore the previous XEX if publishing its report fails."""
    report_path = target.with_suffix(".report.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    staged_paths = []
    previous = target.read_bytes() if target.exists() else None
    try:
        for data in (
            output_bytes,
            (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
        ):
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as staged:
                staged_paths.append(Path(staged.name))
                staged.write(data)
        if previous is not None:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as backup:
                staged_paths.append(Path(backup.name))
                backup.write(previous)
        os.replace(staged_paths[0], target)
        try:
            os.replace(staged_paths[1], report_path)
        except Exception:
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                os.replace(staged_paths[2], target)
            raise
    finally:
        for path in staged_paths:
            path.unlink(missing_ok=True)


def build(
    source: Path, target: Path, tool: Path, colors, media="hdd", overwrite=False, extension=None
) -> dict:
    source, target, tool = source.resolve(), target.resolve(), tool.resolve()
    from animations import source as bundled_source

    report_path = target.with_suffix(".report.json")
    if target == bundled_source("modern").resolve():
        raise ValueError("Die Eingabedatei darf nicht überschrieben werden.")
    if target == source or report_path == source:
        raise ValueError("Die Eingabedatei darf nicht überschrieben werden.")
    if target == tool or report_path == tool:
        raise ValueError("XexTool darf nicht überschrieben werden.")
    if not tool.is_file() or not source.is_file():
        raise ValueError("Eingabedatei oder XexTool fehlt.")
    if not overwrite and (target.exists() or report_path.exists()):
        raise ValueError("Ausgabedatei oder Prüfbericht existiert bereits.")
    if media not in ("hdd", "flash"):
        raise ValueError("Unbekanntes Ausgabeziel.")
    if len(colors) != 3 or any(
        len(c) != 3 or any(not math.isfinite(v) or not 0 <= v <= 1 for v in c) for c in colors
    ):
        raise ValueError("Drei RGB-Farben mit Werten zwischen 0 und 1 erforderlich.")
    source_before = source.read_bytes()
    with tempfile.TemporaryDirectory(prefix="native-boot-color-") as temp:
        temp = Path(temp)
        # Always operate on a copy: XexTool can modify its input when -o is omitted.
        copy = temp / "input.xex"
        copy.write_bytes(source_before)
        raw = temp / "raw.xex"
        logs = [run_tool(tool, "-e", "u", "-c", "u", "-o", raw, copy)]
        raw_bytes = bytearray(raw.read_bytes())
        payload, before = read_uncompressed(raw_bytes)
        changes = []
        for (label, offset, _), rgb in zip(SLOTS, colors):
            old = struct.unpack_from(">4f", before, offset)
            struct.pack_into(">3f", raw_bytes, payload + offset, *rgb)
            new = struct.unpack_from(">4f", raw_bytes, payload + offset)
            changes.append(
                {"label": label, "image_offset": hex(offset), "before_rgba": old, "after_rgba": new}
            )
        extra_allowed, hooks = set(), []
        if extension is not None:
            from native_extension import patch

            verify_hook_pages(raw_bytes)
            updated, extra_allowed, hooks = patch(
                bytes(raw_bytes[payload : payload + len(before)]), extension
            )
            raw_bytes[payload : payload + len(before)] = updated
        expected = bytes(raw_bytes[payload : payload + len(before)])
        raw.write_bytes(raw_bytes)
        packed = temp / "packed.xex"
        args = ["-c", "c"]
        if media == "hdd":
            args += ["-r", "mb"]  # Media and bounding path only; retain DLL flags/exports.
        logs.append(run_tool(tool, *args, "-o", packed, raw))
        extracted = temp / "roundtrip.image"
        logs.append(run_tool(tool, "-b", extracted, packed))
        actual = extracted.read_bytes()
        if actual != expected:
            raise RuntimeError("Rückprüfung fehlgeschlagen: entpacktes Programmabbild weicht ab.")
        changed = [i for i, (a, b) in enumerate(zip(before, actual)) if a != b]
        allowed = {o + j for _, o, _ in SLOTS for j in range(12)} | extra_allowed
        if not set(changed) <= allowed:
            raise RuntimeError(
                "Änderungen außerhalb der freigegebenen Parameter und Material-Hooks gefunden."
            )
        output_bytes = packed.read_bytes()
        if extension is not None:
            verify_hook_pages(output_bytes)
        if word(output_bytes, 4) != 9:
            raise RuntimeError("Title-/DLL-Flags gingen verloren.")
        sec = word(output_bytes, 16)
        if word(output_bytes, sec + 0x160) != 0x98058304:
            raise RuntimeError("Exporttabelle ging verloren.")
        input_media, input_path = media_bindings(source_before)
        output_media, output_path = media_bindings(output_bytes)
        if media == "hdd" and (output_media != 0xFFFFFFFF or output_path is not None):
            raise RuntimeError("Medien-/Pfadbindung wurde für HDD nicht vollständig entfernt.")
        if media == "flash" and (output_media != input_media or output_path != input_path):
            raise RuntimeError("Die ursprüngliche Medien-/Pfadbindung wurde für NAND verändert.")
        if source.read_bytes() != source_before:
            raise RuntimeError("Die Eingabedatei wurde während des Exports geändert.")
        report = {
            "status": "EXPERIMENTAL_UNTESTED_ON_CONSOLE",
            "source": str(source),
            "source_sha256": sha(source_before),
            "output": str(target),
            "output_sha256": sha(output_bytes),
            "reference_image_sha256": IMAGE_SHA256,
            "output_image_sha256": sha(actual),
            "media_target": media,
            "media_bindings_verified": True,
            "allowed_media_before": hex(input_media),
            "allowed_media_after": hex(output_media),
            "bounding_path_before": input_path.hex() if input_path is not None else None,
            "bounding_path_after": output_path.hex() if output_path is not None else None,
            "changed_byte_count": len(changed),
            "changed_image_offsets": [hex(i) for i in changed],
            "changes": changes,
            "roundtrip_equal": True,
            "native_code_unchanged": before[0xE000:0x59000] == actual[0xE000:0x59000],
            "audio_unchanged": True,
            "material_hooks": hooks,
            "studio_profile": extension,
            "procedural_texture_hooks": (
                ["0x2046c", "0x20930"]
                if extension and extension.get("texture_tint") is not None
                else []
            ),
            "ribbon_vertex_hooks": (
                ["0x1b510", "0x1bb08"]
                if extension and extension.get("ribbon_tint") is not None
                else []
            ),
            "background_hook": (
                "0x11ef0" if extension and extension.get("background_color") is not None else None
            ),
            "background_color": extension.get("background_color") if extension else None,
            "preview": "ORIGINAL_MESHES_APPROXIMATE_LIGHTING_AND_MOTION" if extension else None,
            "title_dll_flags": 9,
            "export_table": "0x98058304",
            "xextool_sha256": sha(tool.read_bytes()),
            "xextool_logs": logs,
        }
        publish_export(target, output_bytes, report)
        return report


def find_tool() -> Path:
    """Resolve a user-supplied tool without searching unrelated workspaces."""
    selected = os.environ.get("NBS_XEXTOOL")
    return Path(selected) if selected else app_dir() / "tools" / "xextool.exe"
