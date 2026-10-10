"""Decode original bootanim mesh data. Preview lighting/motion are approximate.

Geometry is decoded from the verified, bundled modern XEX.
"""

import math
import struct
from collections import OrderedDict
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from i18n import t

_CACHE = OrderedDict()


def prepared(scene):
    key = id(scene)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key][1]
    result = []
    for vertices, triangles in scene[0]:
        faces = []
        for a, b, c in triangles:
            p, q, r = vertices[a], vertices[b], vertices[c]
            u, v = [q[i] - p[i] for i in range(3)], [r[i] - p[i] for i in range(3)]
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            length = math.sqrt(sum(x * x for x in n))
            if length > 1e-10:
                faces.append(((a, b, c), tuple(x / length for x in n)))
        result.append(faces)
    _CACHE[key] = (scene, result)
    while len(_CACHE) > 3:
        _CACHE.popitem(last=False)
    return result


def decode_indices(data, offset, size):
    end, value, indices = offset + size, 0, []
    while offset < end:
        delta = struct.unpack_from("b", data, offset)[0]
        offset += 1
        if delta == -128:
            if offset + 2 > end:
                raise ValueError("Truncated native index stream")
            delta = struct.unpack_from("<h", data, offset)[0]
            offset += 2
        value = (value + delta) & 65535
        indices.append(value)
    return indices


def extract(data):
    f = lambda off: struct.unpack_from(">f", data, off)[0]
    meshes = []
    # Native decoders at 0x188a0 (XYZ) and 0x18bc8 (XYZ/UV).
    definitions = [
        (0x6AC50, 0x6DC8, 3, 0x28A4, 0x71A18, 0x39BC),
        (0x68B40, 0x1DC4, 5, 0x2884, 0x6A908, 0x346),
        (0x63510, 0x4682, 5, 0x2894, 0x67B98, 0xFA4),
    ]
    for off, size, stride, const, io, ins in definitions:
        vertices = [
            tuple(v / f(const) + f(const + 4) for v in struct.unpack_from(">3h", data, p))
            for p in range(off, off + size, stride * 2)
        ]
        indices = decode_indices(data, io, ins)
        if max(indices) >= len(vertices):
            raise ValueError("Native mesh indices do not match vertices")
        triangles = [
            (
                tuple(indices[i : i + 3])
                if i % 2 == 0
                else (indices[i + 1], indices[i], indices[i + 2])
            )
            for i in range(len(indices) - 2)
        ]
        meshes.append((vertices, triangles))
    texts = []
    base = 0
    for descriptor in (0x631CC, 0x631E0, 0x631F4):
        _, _, nv, nt, _, z, _, ip = struct.unpack_from(">BBHHHfII", data, descriptor)
        vertices = [
            (
                struct.unpack_from(">H", data, 0x61390 + 2 * i)[0] * f(0x25E8) - f(0x25EC),
                struct.unpack_from(">H", data, 0x61980 + 2 * i)[0] * f(0x25F0) - f(0x25F4),
                z,
            )
            for i in range(base, base + nv)
        ]
        indices = struct.unpack_from(">" + "H" * (nt * 3), data, ip - 0x98000000)
        if max(indices) >= nv:
            raise ValueError("Native text indices do not match vertices")
        texts.append((vertices, [tuple(indices[i : i + 3]) for i in range(0, nt * 3, 3)]))
        base += nv
    return meshes, texts


def hexcolor(rgb):
    return "#" + "".join(f"{min(255,max(0,round(c*255))):02x}" for c in rgb)


def render(
    scene,
    profile,
    size=(800, 450),
    time=7.0,
    orbit=0.0,
    isolated=None,
    background="#f5f5f5",
    zoom=1.0,
    text_only=False,
):
    """Original triangles, CPU painter rendering; not an Xbox GPU emulation."""
    w, h = size
    image = Image.new("RGB", size, background)
    # Approximate preview phases; original native animation curves stay untouched.
    phase = max(0.0, min(1.0, (time - 1.5) / 3.5))
    angle = orbit + (1 - phase) * 2.4
    ca, sa = math.cos(angle), math.sin(angle)
    scale = h * 0.27 * (0.7 + 0.3 * phase) * zoom
    cx, cy = w * 0.5, h * 0.36
    # Simplified visual reference for the three native GPU color parameters.
    glow = Image.new("RGB", size, background)
    glow_draw = ImageDraw.Draw(glow)
    color = profile["effects"][0]
    base = tuple(int(background[i : i + 2], 16) / 255 for i in (1, 3, 5))
    pale = tuple(base[i] * 0.92 + 0.08 * c for i, c in enumerate(color))
    glow_draw.ellipse(
        (cx - scale * 1.12, cy - scale * 1.12, cx + scale * 1.12, cy + scale * 1.12),
        fill=hexcolor(pale),
    )
    image = glow.filter(ImageFilter.GaussianBlur(max(2, scale * 0.18)))
    draw = ImageDraw.Draw(image)
    all_triangles = []
    cached = prepared(scene)
    for material, (vertices, triangles) in enumerate(scene[0]):
        if text_only or (
            isolated is not None
            and material not in (isolated if isinstance(isolated, tuple) else (isolated,))
        ):
            continue
        transformed = [(ca * x + sa * z, y, -sa * x + ca * z) for x, y, z in vertices]
        # Preview view orientation only; native camera curves are not exported.
        transformed = [
            ((x - y) * math.sqrt(0.5), (x + y) * math.sqrt(0.5), z) for x, y, z in transformed
        ]
        color = profile["materials"][material]["diffuse"]
        if material in (1, 2):
            effect = profile.get("shader_colors", profile["effects"])[1 if material == 2 else 0]
            if profile.get("texture_tint") is not None:
                effect = [(80 + 144 * c) / 255 for c in profile["texture_tint"]]
            color = tuple(color[i] * (0.15 + 1.8 * effect[i]) for i in range(3))
        spec = profile["materials"][material]["specular"]
        for (a, b, c), normal in cached[material]:
            points = [transformed[j] for j in (a, b, c)]
            nx, ny, nz = normal
            nx, nz = ca * nx + sa * nz, -sa * nx + ca * nz
            nx, ny = (nx - ny) * math.sqrt(0.5), (nx + ny) * math.sqrt(0.5)
            light = abs(nx * -0.3 + ny * 0.5 + nz * 0.8)
            rgb = tuple(
                min(1.0, color[i] * (0.45 + 0.9 * light) + spec[i] * light**24 * 0.3) ** (1 / 2.2)
                for i in range(3)
            )
            all_triangles.append((sum(p[2] for p in points), points, hexcolor(rgb)))
    for _, points, fill in sorted(all_triangles, key=lambda t: t[0]):
        draw.polygon([(cx + x * scale, cy - y * scale) for x, y, z in points], fill=fill)
    if isolated is None and scene[1]:
        # Native text XY, independently editable transform as in exported XEX.
        transform = profile["text_transform"]
        tx, ty, ts = transform["x"], transform["y"], transform["scale"]
        xs = [x for vs, _ in scene[1] for x, y, z in vs]
        ys = [y for vs, _ in scene[1] for x, y, z in vs]
        mx, my = (min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5
        for index, (vs, triangles) in enumerate(scene[1]):
            col = profile["text_colors"][index]
            for tri in triangles:
                points = []
                for j in tri:
                    x, y, _ = vs[j]
                    x, y = mx + (x - mx) * ts + tx, my + (y - my) * ts + ty
                    points.append(
                        (
                            w * 0.5 + x * h * 0.18 * zoom,
                            (h * 0.40 if text_only else h * 0.56) - y * h * 0.18 * zoom,
                        )
                    )
                draw.polygon(points, fill=hexcolor(col))
    return image


def native_color_samples(profile):
    """Actual input colors and the same channel transform as the native hooks."""
    samples = []
    for name, rgb, key, selective in [
        ("Wirbel · dunkel", [0.0031372549, 0.2698039114, 0.0564705878], "ribbon_tint", True),
        ("Wirbel · mittel", [0.387, 0.636, 0.0], "ribbon_tint", True),
        ("Wirbel · hell", [0.9764705896, 0.9882352948, 0.2901960909], "ribbon_tint", True),
        ("Kugel-X · Textur", [209 / 255, 224 / 255, 80 / 255], "texture_tint", False),
        ("Kugel-X · dunkel", [80 / 255, 160 / 255, 40 / 255], "texture_tint", False),
    ]:
        tint = profile.get(key)
        if tint is not None and (not selective or rgb[1] > max(rgb[0], rgb[2])):
            rgb = [rgb[2] + (rgb[1] - rgb[2]) * c for c in tint]
        samples.append((name, rgb))
    return samples


def font(size):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size)
    except OSError:
        return ImageFont.load_default()


def render_samples(profile, size, background):
    w, h = size
    image = Image.new("RGB", size, background)
    draw = ImageDraw.Draw(image)
    dark = sum(int(background[i : i + 2], 16) for i in (1, 3, 5)) < 380
    fg = "#d9e5f5" if dark else "#243650"
    pad = max(20, w // 15)
    row = min(78, (h - 50) // 5)
    top = max(10, (h - row * 5) // 2)
    for i, (name, rgb) in enumerate(native_color_samples(profile)):
        y = top + i * row
        draw.text((pad, y), t(name), font=font(max(11, min(17, w // 30))), fill=fg)
        draw.text((w - pad - 80, y), hexcolor(rgb).upper(), font=font(13), fill=fg)
        for x in range(pad, w - pad):
            progress = (x - pad) / max(1, w - 2 * pad - 1)
            shade = [c + (1 - c) * progress * 0.85 for c in rgb]
            draw.line((x, y + 28, x, y + 48), fill=hexcolor(shade))
    return image


def render_view(
    scene,
    profile,
    size,
    time=7.0,
    orbit=0.0,
    mode="Gesamtbild",
    compare=False,
    dark=False,
    zoom=1.0,
):
    def backdrop(p):
        color = p.get("background_color")
        return hexcolor(color) if color is not None else ("#111a2a" if dark else "#f5f5f5")

    background = backdrop(profile)

    def one(p, s):
        color = backdrop(p)
        if mode == "Farbverläufe":
            return render_samples(p, s, color)
        isolated = {"Kugel": (0, 1, 2), "Kugel-X": (1, 2), "Oberfläche": 0}.get(mode)
        return render(scene, p, s, time, orbit, isolated, color, zoom, mode == "Schriftzug")

    if not compare:
        return one(profile, size)
    from native_extension import defaults

    w, h = size
    half = (w - 2) // 2
    image = Image.new("RGB", size, "#17263c")
    image.paste(one(defaults(), (half, h - 30)), (0, 30))
    image.paste(one(profile, (w - half - 2, h - 30)), (half + 2, 30))
    draw = ImageDraw.Draw(image)
    fg = "#e8f0fc"
    draw.text((18, 6), t("Original"), font=font(14), fill=fg)
    draw.text((half + 20, 6), t("Dein Entwurf"), font=font(14), fill=fg)
    draw.line((half + 1, 0, half + 1, h), fill="#344763" if dark else "#d5deea")
    return image
