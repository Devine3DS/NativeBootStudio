"""Version-specific native material hooks and quantized text transforms.

Offsets are valid only for the SHA256-verified 17559 image accepted by the backend.
"""

import copy
import colorsys
import math
import struct

MATERIAL_NAMES = [
    "Kugeloberfläche",
    "Kanten der Vertiefung",
    "Flächen der Vertiefung",
    "Inneres Kugelmodell A",
    "Inneres Kugelmodell B",
]
TEXT_NAMES = ["XBOX", "360", "Markenzeichen"]
HOOKS = [
    (0x1E7B0, 0x394100B0, 0),
    (0x1E870, 0x394100C0, 1),
    (0x1E930, 0x394100C0, 2),
    (0x1E9EC, 0x394100B0, 3),
    (0x1EAA8, 0x394100B0, 4),
    (0x1EB94, 0x8087000C, 5),
    (0x1EC08, 0x81480004, 6),
    (0x1EC4C, 0x39410050, 7),
    (0x1ECA0, 0x39410050, 7),
]
PALETTE, CAVE_END, CODE = 0x58340, 0x59000, 0x58400
SPEED_VALUE = 0x583C0
SPEED_SITES = {0xFCE4: 0x3D409800, 0xFD04: 0xC00A21F0, 0xFDF8: 0x3D009800, 0xFE14: 0xC3E821F0}
SHADER_COLOR_OFFSETS = (0xC38, 0xC48)
TEXTURE_TINT_VALUE, TEXTURE_CODE = 0x583D0, 0x58600
# fctidz at the RGB packers, after procedural noise/color interpolation.
TEXTURE_SITES = ((0x2046C, (7, 9, 8), 12, 11), (0x20930, (12, 11, 0), 10, 9))
RIBBON_TINT_VALUE, RIBBON_CODE = 0x583E0, 0x58700
RIBBON_SITES = (0x1B510, 0x1BB08)
RIBBON_ORIGINAL = (0xED9DB5F8, 0x39610080)
BACKGROUND_VALUE, BACKGROUND_CODE = 0x583F0, 0x58800
BACKGROUND_SITE = 0x11EF0
# Full-screen gradient shader at 0x2418. Its final 12-byte padding becomes a MUL.
BACKGROUND_SHADER_WORDS = {0x252C: 0x5001C400, 0x2564: 0xC88FC000, 0x2570: 0, 0x2574: 0, 0x2578: 0}


def defaults():
    return {
        "format": "native-boot-studio",
        "version": 2,
        "effects": [[0.69, 0.94, 0.22], [0.75, 1, 0.75], [0.05, 0.35, 0.06]],
        "materials": [
            {"diffuse": [0.26] * 3, "specular": [0.55 if i in (0, 3, 4) else 0.67] * 3}
            for i in range(5)
        ],
        "text_colors": [
            [119 / 255, 187 / 255, 68 / 255],
            [164 / 255, 164 / 255, 167 / 255],
            [164 / 255, 164 / 255, 167 / 255],
        ],
        "text_transform": {"scale": 1.0, "x": 0.0, "y": 0.0},
        "animation_speed": 1.0,
        "shader_colors": [[0.3, 0.88, 0.12], [10 / 255, 165 / 255, 80 / 255]],
        "texture_tint": None,
        "ribbon_tint": None,
        "background_color": None,
    }


def profile_preset(name, effects):
    p = defaults()
    p["effects"] = [list(c) for c in effects]
    if name != "original":
        hue = {"blue": 7 / 12, "cyan": 0.5, "purple": 5 / 6}[name]
        p["effects"] = [
            list(colorsys.hsv_to_rgb(hue, *colorsys.rgb_to_hsv(*rgb)[1:])) for rgb in p["effects"]
        ]
        p["text_colors"][0] = list(p["effects"][0])
        p["texture_tint"] = list(colorsys.hsv_to_rgb(hue, 1.0, 1.0))
        p["ribbon_tint"] = list(p["texture_tint"])
        p["shader_colors"] = [
            list(colorsys.hsv_to_rgb(hue, *colorsys.rgb_to_hsv(*rgb)[1:]))
            for rgb in p["shader_colors"]
        ]
    return p


def validate(p):
    if not isinstance(p, dict) or p.get("format") != "native-boot-studio" or p.get("version") != 2:
        raise ValueError("Unbekanntes Projektformat.")
    original = defaults()
    p = copy.deepcopy(p)
    p.setdefault("animation_speed", 1.0)
    # Older projects retain the old shader colors until a new preset is chosen.
    p.setdefault("shader_colors", copy.deepcopy(original["shader_colors"]))
    p.setdefault("texture_tint", None)
    p.setdefault("ribbon_tint", None)
    p.setdefault("background_color", None)
    v = p["animation_speed"]
    if (
        isinstance(v, bool)
        or not isinstance(v, (int, float))
        or not math.isfinite(v)
        or not 0.75 <= v <= 1.25
    ):
        raise ValueError("Animationstempo muss zwischen 0,75 und 1,25 liegen.")
    for key, count in [("effects", 3), ("materials", 5), ("text_colors", 3), ("shader_colors", 2)]:
        if len(p[key]) != count:
            raise ValueError("Ungültige Anzahl von Farbparametern.")
    for rgb in (
        p["effects"]
        + p["text_colors"]
        + p["shader_colors"]
        + [m["diffuse"] for m in p["materials"]]
    ):
        if len(rgb) != 3 or any(
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            or not 0 <= v <= 1
            for v in rgb
        ):
            raise ValueError("Ungültige RGB-Werte im Projekt.")
    for key in ("texture_tint", "ribbon_tint", "background_color"):
        tint = p[key]
        if tint is not None and (
            not isinstance(tint, list)
            or len(tint) != 3
            or any(
                isinstance(v, bool)
                or not isinstance(v, (int, float))
                or not math.isfinite(v)
                or not 0 <= v <= 1
                for v in tint
            )
        ):
            raise ValueError("Ungültige Farbe für Texturen oder Wirbel.")
    # Specular values are not editable: native runtime pulses modify them.
    if [m["specular"] for m in p["materials"]] != [m["specular"] for m in original["materials"]]:
        raise ValueError("Glanzwerte sind in dieser Version nicht editierbar.")
    t = p["text_transform"]
    for key, lo, hi in [("scale", 0.6, 1.1), ("x", -0.3, 0.3), ("y", -0.18, 0.18)]:
        v = t[key]
        if (
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            or not lo <= v <= hi
        ):
            raise ValueError("Schriftzug-Transformation außerhalb des unterstützten Bereichs.")
    return copy.deepcopy(p)


def branch(source, dest):
    displacement = dest - source
    if displacement % 4 or not -(1 << 25) <= displacement < (1 << 25):
        raise ValueError("PowerPC branch out of range")
    return 0x48000000 | (displacement & 0x03FFFFFC)


def texture_hook_words(site, rgb, diff, coefficient, start, displaced):
    """Project the green gradient to RGB: B + (G-B)*tint.

    Both generators retain their original noise, intensity, alpha and mipmaps.
    Equal RGB values stay equal. All source registers are dead after packing,
    apart from the RGB results consumed by the original fctidz instructions.
    """
    red, green, blue = rgb
    words = [
        0x3D809806,  # lis r12,0x9806
        (59 << 26) | (diff << 21) | (green << 16) | (blue << 11) | (20 << 1),
    ]
    for i, dest in enumerate(rgb):
        words += [
            (48 << 26)
            | (coefficient << 21)
            | (12 << 16)
            | ((TEXTURE_TINT_VALUE + 4 * i - 0x60000) & 65535),
            (59 << 26)
            | (dest << 21)
            | (diff << 16)
            | (blue << 11)
            | (coefficient << 6)
            | (29 << 1),
        ]
    words += [displaced, branch(start + 4 * len(words) + 4, site + 4)]
    return words


def ribbon_hook_words(site, start, displaced):
    """Tint green-dominant vertex colors after either native color source.

    f0/f13 (widths), f14..f31 (animation constants) and stack alpha are live.
    Only f10..f12, r12 and CR6 are scratch. CR6 is overwritten before its next
    native use at both sites. The displaced instruction executes on both paths.
    """
    words = [
        0x3D809806,
        0xC1410080,
        0xC1610084,
        0xC1810088,
        (63 << 26) | (6 << 23) | (11 << 16) | (12 << 11),  # fcmpu cr6,f11,f12
        0,  # ble cr6,restore: preserve blue/white/gray
        (63 << 26) | (6 << 23) | (11 << 16) | (10 << 11),
        0,
        (59 << 26) | (11 << 21) | (11 << 16) | (12 << 11) | (20 << 1),
    ]
    for i in range(3):
        words += [
            (48 << 26) | (10 << 21) | (12 << 16) | ((RIBBON_TINT_VALUE + 4 * i - 0x60000) & 65535),
            (59 << 26) | (10 << 21) | (11 << 16) | (12 << 11) | (10 << 6) | (29 << 1),
            (52 << 26) | (10 << 21) | (1 << 16) | (0x80 + 4 * i),
        ]
    restore = len(words)
    for index in (5, 7):
        words[index] = 0x40990000 | ((restore - index) * 4)
    words += [displaced, branch(start + 4 * (restore + 1), site + 4)]
    return words


def patch(before, profile):
    p = validate(profile)
    image, allowed, hooks = bytearray(before), set(), []
    original = defaults()
    for off, rgb in zip(SHADER_COLOR_OFFSETS, p["shader_colors"]):
        replacement = struct.pack(">3f", *rgb)
        if replacement != before[off : off + 12]:
            image[off : off + 12] = replacement
            allowed.update(range(off, off + 12))
    colors = [m["diffuse"] for m in p["materials"]] + p["text_colors"]
    original_colors = [m["diffuse"] for m in original["materials"]] + original["text_colors"]
    if colors != original_colors:
        if any(image[PALETTE:CAVE_END]):
            raise ValueError("Der reservierte Codebereich ist nicht leer.")
        for index, rgb in enumerate(colors):
            struct.pack_into(">4f", image, PALETTE + 16 * index, *rgb, 1.0)
        pc = CODE
        # All nine hooks are installed together. Each resets the reused stack RGB
        # before its native material copy; alpha, specular and ambient stay native.
        for offset, displaced, index in HOOKS:
            if struct.unpack_from(">I", image, offset)[0] != displaced:
                raise ValueError("Unerwartete Instruktion am Material-Hook.")
            start = pc
            words = [0x3D809806]  # lis r12,0x9806; r12/f12 are dead at these sites
            for component in range(3):
                imm = (PALETTE + 16 * index + 4 * component - 0x60000) & 0xFFFF
                words += [
                    (48 << 26) | (12 << 21) | (12 << 16) | imm,  # lfs f12,imm(r12)
                    (52 << 26) | (12 << 21) | (1 << 16) | (0x50 + 4 * component),
                ]
            words += [displaced, branch(pc + len(words) * 4 + 4, offset + 4)]
            blob = struct.pack(">" + "I" * len(words), *words)
            if pc + len(blob) > CAVE_END:
                raise ValueError("Material-Hooks überschreiten den Codebereich.")
            image[pc : pc + len(blob)] = blob
            struct.pack_into(">I", image, offset, branch(offset, pc))
            allowed.update(range(offset, offset + 4))
            hooks.append(
                {
                    "site": hex(offset),
                    "trampoline": hex(start),
                    "color_index": index,
                    "displaced_instruction": hex(displaced),
                    "length": len(blob),
                }
            )
            pc += len(blob)
        allowed.update(range(PALETTE, PALETTE + len(colors) * 16))
        allowed.update(range(CODE, pc))
    t = p["text_transform"]
    if t != original["text_transform"]:
        count = 760
        for array, scale_offset, bias_offset, translation in [
            (0x61390, 0x25E8, 0x25EC, t["x"]),
            (0x61980, 0x25F0, 0x25F4, t["y"]),
        ]:
            scale = struct.unpack_from(">f", before, scale_offset)[0]
            bias = struct.unpack_from(">f", before, bias_offset)[0]
            encoded = struct.unpack_from(">" + "H" * count, before, array)
            coords = [v * scale - bias for v in encoded]
            center = (min(coords) + max(coords)) * 0.5
            # Port the affine transform into the native dequantizer coefficients.
            # This keeps every original index and quantized vertex intact and
            # avoids clipping at the uint16 storage boundaries.
            struct.pack_into(">f", image, scale_offset, scale * t["scale"])
            struct.pack_into(
                ">f",
                image,
                bias_offset,
                bias * t["scale"] - center * (1 - t["scale"]) - translation,
            )
            allowed.update(range(scale_offset, scale_offset + 4))
            allowed.update(range(bias_offset, bias_offset + 4))
    if p["animation_speed"] != 1.0:
        if any(before[PALETTE:CAVE_END]):
            raise ValueError("Der reservierte Codebereich ist nicht leer.")
        for off, value in SPEED_SITES.items():
            if struct.unpack_from(">I", before, off)[0] != value:
                raise ValueError("Unerwartete Instruktion in der nativen Zeitberechnung.")
        seconds_per_ms = struct.unpack_from(">f", before, 0x21F0)[0]
        struct.pack_into(">f", image, SPEED_VALUE, seconds_per_ms * p["animation_speed"])
        imm = (SPEED_VALUE - 0x60000) & 65535
        replacements = {
            0xFCE4: 0x3D409806,
            0xFD04: 0xC00A0000 | imm,
            0xFDF8: 0x3D009806,
            0xFE14: 0xC3E80000 | imm,
        }
        for off, value in replacements.items():
            struct.pack_into(">I", image, off, value)
            allowed.update(range(off, off + 4))
        allowed.update(range(SPEED_VALUE, SPEED_VALUE + 4))
    if p["texture_tint"] is not None:
        if any(before[PALETTE:CAVE_END]):
            raise ValueError("Der reservierte Codebereich ist nicht leer.")
        struct.pack_into(">3f", image, TEXTURE_TINT_VALUE, *p["texture_tint"])
        allowed.update(range(TEXTURE_TINT_VALUE, TEXTURE_TINT_VALUE + 12))
        pc = TEXTURE_CODE
        for site, rgb, diff, coefficient in TEXTURE_SITES:
            displaced = struct.unpack_from(">I", before, site)[0]
            # Verify fctidz destination/source, rather than accepting other opcodes.
            fd, fs = (6, 9) if site == 0x2046C else (11, 11)
            if displaced != (63 << 26) | (fd << 21) | (fs << 11) | (815 << 1):
                raise ValueError("Unerwartete Instruktion am Textur-Hook.")
            words = texture_hook_words(site, rgb, diff, coefficient, pc, displaced)
            blob = struct.pack(">" + "I" * len(words), *words)
            if pc + len(blob) > CAVE_END:
                raise ValueError("Textur-Hooks überschreiten den Codebereich.")
            image[pc : pc + len(blob)] = blob
            struct.pack_into(">I", image, site, branch(site, pc))
            allowed.update(range(site, site + 4))
            allowed.update(range(pc, pc + len(blob)))
            pc += len(blob)
    if p["ribbon_tint"] is not None:
        if any(before[PALETTE:CAVE_END]):
            raise ValueError("Der reservierte Codebereich ist nicht leer.")
        struct.pack_into(">3f", image, RIBBON_TINT_VALUE, *p["ribbon_tint"])
        allowed.update(range(RIBBON_TINT_VALUE, RIBBON_TINT_VALUE + 12))
        pc = RIBBON_CODE
        for site, displaced in zip(RIBBON_SITES, RIBBON_ORIGINAL):
            if struct.unpack_from(">I", before, site)[0] != displaced:
                raise ValueError("Unerwartete Instruktion am Wirbel-Hook.")
            words = ribbon_hook_words(site, pc, displaced)
            blob = struct.pack(">" + "I" * len(words), *words)
            if pc + len(blob) > CAVE_END:
                raise ValueError("Wirbel-Hooks überschreiten den Codebereich.")
            image[pc : pc + len(blob)] = blob
            struct.pack_into(">I", image, site, branch(site, pc))
            allowed.update(range(site, site + 4))
            allowed.update(range(pc, pc + len(blob)))
            pc += len(blob)
    if p["background_color"] is not None:
        if any(before[PALETTE:CAVE_END]):
            raise ValueError("Der reservierte Codebereich ist nicht leer.")
        for off, value in BACKGROUND_SHADER_WORDS.items():
            if struct.unpack_from(">I", before, off)[0] != value:
                raise ValueError("Unerwarteter Hintergrund-Shader.")
        displaced = 0xD06B178C  # stfs f3,0x178c(r11)
        if struct.unpack_from(">I", before, BACKGROUND_SITE)[0] != displaced:
            raise ValueError("Unerwartete Instruktion am Hintergrund-Hook.")
        # c0.x remains the original animated gradient/fade. c0.yzw was unused
        # by this shader; fill it with RGB. r12/f12 are dead at this call site.
        struct.pack_into(">3f", image, BACKGROUND_VALUE, *p["background_color"])
        words = [displaced, 0x3D809806]
        for i in range(3):
            words += [
                0xC18C0000 | ((BACKGROUND_VALUE + 4 * i - 0x60000) & 65535),
                0xD18B0000 | (0x1784 + 4 * i),
            ]
        words.append(branch(BACKGROUND_CODE + 4 * len(words), BACKGROUND_SITE + 4))
        blob = struct.pack(">" + "I" * len(words), *words)
        image[BACKGROUND_CODE : BACKGROUND_CODE + len(blob)] = blob
        struct.pack_into(">I", image, BACKGROUND_SITE, branch(BACKGROUND_SITE, BACKGROUND_CODE))
        # Execute 6 instead of 5 ALUs, compute the original grayscale into r0,
        # then export RGB = r0 * c0.yzw. Alpha stays the original constant one.
        # Reuse r0 so shader temporary-register allocation stays unchanged.
        replacements = {
            0x252C: 0x6001C400,
            0x2564: 0xC8070000,
            0x2570: 0xC88FC000,
            0x2574: 0x00001500,
            0x2578: 0xA1000000,
        }
        for off, value in replacements.items():
            struct.pack_into(">I", image, off, value)
            allowed.update(range(off, off + 4))
        allowed.update(range(BACKGROUND_SITE, BACKGROUND_SITE + 4))
        allowed.update(range(BACKGROUND_VALUE, BACKGROUND_VALUE + 12))
        allowed.update(range(BACKGROUND_CODE, BACKGROUND_CODE + len(blob)))
    return image, allowed, hooks
