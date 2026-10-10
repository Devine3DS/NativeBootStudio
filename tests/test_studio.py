import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import native_boot_color as b
import native_extension as e
import scene

TOOL = b.find_tool()
RAW_XEX = IMAGE = None
if TOOL.is_file() and b.DEFAULT_INPUT.is_file():
    with tempfile.TemporaryDirectory() as scratch:
        raw_path = Path(scratch) / "original.xex"
        b.run_tool(TOOL, "-e", "u", "-c", "u", "-o", raw_path, b.DEFAULT_INPUT)
        RAW_XEX = raw_path.read_bytes()
        _, IMAGE = b.read_uncompressed(RAW_XEX)


@unittest.skipUnless(
    IMAGE is not None, "Supply NBS_BOOTANIM and NBS_XEXTOOL for native integration tests"
)
class StudioTests(unittest.TestCase):
    def test_original_restores_entire_image(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "original.xex"
            p = e.defaults()
            r = b.build(b.DEFAULT_INPUT, target, TOOL, p["effects"], "flash", False, p)
            self.assertEqual(r["output_image_sha256"], b.IMAGE_SHA256)
            self.assertEqual(r["changed_byte_count"], 0)
            self.assertTrue(r["native_code_unchanged"])

    def test_native_hooks_execute(self):
        p = e.defaults()
        for i in range(5):
            p["materials"][i]["diffuse"] = [(i + 1) / 9, 0.1, 0.87]
        p["text_colors"] = [[0.9, 0.01, 0.04], [0.05, 0.9, 0.07], [0.08, 0.09, 0.9]]
        image, allowed, hooks = e.patch(IMAGE, p)
        self.assertEqual(len(hooks), 9)
        colors = [m["diffuse"] for m in p["materials"]] + p["text_colors"]
        self.assertTrue({i for i, (x, y) in enumerate(zip(IMAGE, image)) if x != y} <= allowed)
        for h in hooks:
            site, pc = int(h["site"], 16), int(h["trampoline"], 16)
            encoded = struct.unpack_from(">I", image, site)[0]
            delta = encoded & 0x3FFFFFC
            if delta & 0x2000000:
                delta -= 0x4000000
            self.assertEqual(site + delta, pc)
            self.assertEqual(encoded & 3, 0)  # no LR write, no absolute addressing
            regs = [0x80000000 + i * 0x1000 for i in range(32)]
            regs[1] = 0x100000
            oldregs = regs[:]
            floats = [float(i) for i in range(32)]
            oldfloats = floats[:]
            mem = {regs[1] + o: struct.pack(">I", 0x3F800000 + o) for o in range(0, 0x200, 4)}
            # Memory for the two displaced lwz instructions.
            for reg, off in [(7, 12), (8, 4)]:
                mem[regs[reg] + off] = struct.pack(">I", 0x12345678)
            beforemem = copy.deepcopy(mem)
            changed_dest = None
            steps = 0
            while pc != site + 4:
                self.assertLess(steps, 12)
                steps += 1
                instr = struct.unpack_from(">I", image, pc)[0]
                op, rt, ra = instr >> 26, (instr >> 21) & 31, (instr >> 16) & 31
                imm = instr & 65535
                if imm & 32768:
                    imm -= 65536
                if op == 15:
                    regs[rt] = (imm << 16) & 0xFFFFFFFF
                elif op == 48:
                    address = (regs[ra] + imm) & 0xFFFFFFFF
                    floats[rt] = struct.unpack_from(">f", image, address - 0x98000000)[0]
                elif op == 52:
                    mem[regs[ra] + imm] = struct.pack(">f", floats[rt])
                elif op == 14:
                    regs[rt] = (regs[ra] + imm) & 0xFFFFFFFF
                    changed_dest = rt
                elif op == 32:
                    regs[rt] = struct.unpack(">I", mem[regs[ra] + imm])[0]
                    changed_dest = rt
                elif op == 18:
                    self.assertEqual(instr & 3, 0)
                    delta = instr & 0x3FFFFFC
                    if delta & 0x2000000:
                        delta -= 0x4000000
                    pc += delta
                    continue
                else:
                    self.fail("Unexpected trampoline opcode")
                pc += 4
            self.assertEqual(steps, 9)
            for i, value in enumerate(colors[h["color_index"]]):
                actual = struct.unpack(">f", mem[regs[1] + 0x50 + 4 * i])[0]
                self.assertAlmostEqual(actual, value, places=6)
            for address, value in beforemem.items():
                if address not in [regs[1] + 0x50 + 4 * i for i in range(3)]:
                    self.assertEqual(mem[address], value)  # alpha and unrelated stack preserved
            for i in range(32):
                if i not in (12, changed_dest):
                    self.assertEqual(regs[i], oldregs[i])
                if i != 12:
                    self.assertEqual(floats[i], oldfloats[i])
            displaced = int(h["displaced_instruction"], 16)
            if displaced >> 26 == 14:
                self.assertEqual(regs[changed_dest], oldregs[1] + (displaced & 65535))
            else:
                self.assertEqual(regs[changed_dest], 0x12345678)

    def test_text_transform_matches_original_mesh(self):
        baseline = scene.extract(IMAGE)[1]
        for scale, dx, dy in [(0.6, 0.3, 0.18), (1.1, -0.3, -0.18), (0.88, 0.1, 0.03)]:
            p = e.defaults()
            p["text_transform"] = {"scale": scale, "x": dx, "y": dy}
            image, allowed, hooks = e.patch(IMAGE, p)
            result = scene.extract(image)[1]
            self.assertFalse(hooks)
            self.assertEqual(len(allowed), 16)
            for axis, delta in [(0, dx), (1, dy)]:
                values = [v[axis] for vs, _ in baseline for v in vs]
                center = (min(values) + max(values)) * 0.5
                for (old, _), (new, _) in zip(baseline, result):
                    for a, z in zip(old, new):
                        self.assertAlmostEqual(
                            z[axis], center + (a[axis] - center) * scale + delta, places=5
                        )
            self.assertEqual(image[0x61390:0x631CC], IMAGE[0x61390:0x631CC])

    def test_extended_export_and_source_integrity(self):
        p = e.profile_preset("cyan", b.preset("cyan"))
        p["materials"][2]["diffuse"] = [0.8, 0.04, 0.09]
        p["text_transform"] = {"scale": 0.8, "x": 0.15, "y": 0.05}
        before = b.DEFAULT_INPUT.read_bytes()
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "bootanim.xex"
            r = b.build(b.DEFAULT_INPUT, target, TOOL, p["effects"], "hdd", False, p)
            self.assertTrue(r["roundtrip_equal"])
            self.assertEqual(len(r["material_hooks"]), 9)
            raw = Path(td) / "result.image"
            b.run_tool(TOOL, "-b", raw, target)
            actual = raw.read_bytes()
            expected, _, _ = e.patch(IMAGE, p)
            for (_, off, _), rgb in zip(b.SLOTS, p["effects"]):
                struct.pack_into(">3f", expected, off, *rgb)
            self.assertEqual(actual, expected)
            self.assertEqual(actual[0x7A000:], IMAGE[0x7A000:])
            self.assertEqual(b.DEFAULT_INPUT.read_bytes(), before)
            # Studio projects retain their original input; v2 XEX re-import is refused.
            with self.assertRaises(ValueError):
                b.build(target, Path(td) / "again.xex", TOOL, p["effects"])

    def test_unknown_input_and_bad_profile_rejected(self):
        p = e.defaults()
        p["materials"][0]["diffuse"] = [float("nan"), 0, 0]
        with self.assertRaises(ValueError):
            e.patch(IMAGE, p)
        p = e.defaults()
        p["text_transform"]["scale"] = 5
        with self.assertRaises(ValueError):
            e.patch(IMAGE, p)
        raw = bytearray(RAW_XEX)
        payload = b.word(raw, 8)
        raw[payload + 0xE000] ^= 1
        with self.assertRaises(ValueError):
            b.read_uncompressed(raw)
        raw = bytearray(RAW_XEX)
        sec = b.word(raw, 16)
        struct.pack_into(">I", raw, sec + 0x184 + 6 * 24, 0x92)
        with self.assertRaises(ValueError):
            b.verify_hook_pages(raw)

    def test_native_speed_two_paths_and_roundtrip(self):
        for speed in (0.75, 1.25):
            p = e.defaults()
            p["animation_speed"] = speed
            changed, allowed, hooks = e.patch(IMAGE, p)
            self.assertFalse(hooks)
            self.assertEqual(len(allowed), 20)
            for lis_off, load_off in [(0xFCE4, 0xFD04), (0xFDF8, 0xFE14)]:
                lis = struct.unpack_from(">I", changed, lis_off)[0]
                load = struct.unpack_from(">I", changed, load_off)[0]
                self.assertEqual(lis >> 26, 15)
                self.assertEqual((lis >> 21) & 31, (load >> 16) & 31)
                base = (lis & 65535) << 16
                low = load & 65535
                if low & 32768:
                    low -= 65536
                off = base + low - 0x98000000
                self.assertEqual(off, e.SPEED_VALUE)
                factor = struct.unpack_from(">f", changed, off)[0]
                native = struct.unpack_from(">f", IMAGE, 0x21F0)[0]
                for ms in (1, 16, 33, 50):
                    self.assertAlmostEqual(ms * factor, ms * native * speed, places=7)
            self.assertEqual(changed[0x21F0:0x21F4], IMAGE[0x21F0:0x21F4])
            with tempfile.TemporaryDirectory() as td:
                r = b.build(
                    b.DEFAULT_INPUT, Path(td) / "tempo.xex", TOOL, p["effects"], "hdd", False, p
                )
                self.assertTrue(r["roundtrip_equal"])
                self.assertFalse(r["native_code_unchanged"])

    def test_preview_live_colors_and_mesh_counts(self):
        native = scene.extract(IMAGE)
        self.assertEqual([len(v) for v, t in native[0]], [4684, 762, 1805])
        self.assertEqual([len(v) for v, t in native[1]], [205, 438, 117])
        p = e.defaults()
        old = scene.render(native, p, (480, 270)).tobytes()
        p["text_colors"][0] = [0.1, 0.2, 0.9]
        self.assertNotEqual(old, scene.render(native, p, (480, 270)).tobytes())
        p = e.defaults()
        p["effects"][0] = [0.1, 0.1, 0.9]
        self.assertNotEqual(old, scene.render(native, p, (480, 270)).tobytes())

    def test_shader_colors_preserve_gpu_instructions(self):
        p = e.defaults()
        p["shader_colors"] = [[0.12, 0.12, 0.88], [10 / 255, 10 / 255, 165 / 255]]
        result, allowed, hooks = e.patch(IMAGE, p)
        self.assertFalse(hooks)
        self.assertEqual(allowed, set(range(0xC38, 0xC44)) | set(range(0xC48, 0xC54)))
        for off, rgb in zip(e.SHADER_COLOR_OFFSETS, p["shader_colors"]):
            for actual, expected in zip(struct.unpack_from(">3f", result, off), rgb):
                self.assertAlmostEqual(actual, expected, places=6)
            self.assertEqual(result[off + 12 : off + 16], IMAGE[off + 12 : off + 16])
        self.assertEqual(result[0xC58:0xD60], IMAGE[0xC58:0xD60])
        old = {"format": "native-boot-studio", "version": 2, **e.defaults()}
        old.pop("shader_colors")
        self.assertEqual(e.validate(old)["shader_colors"], e.defaults()["shader_colors"])

    def test_procedural_texture_hooks_execute_rgb_and_preserve_alpha(self):
        def f32(x):
            return struct.unpack(">f", struct.pack(">f", x))[0]

        for tint in ([0.0, 0.5, 1.0], [0.0, 1.0, 1.0], [1.0, 0.0, 1.0], [0.2, 0.4, 0.8]):
            p = e.defaults()
            p["texture_tint"] = tint
            image, allowed, hooks = e.patch(IMAGE, p)
            self.assertFalse(hooks)
            self.assertTrue({i for i, (x, y) in enumerate(zip(IMAGE, image)) if x != y} <= allowed)
            # Native gradients from both generators, interpolated colors and white.
            for rgb in [
                (209, 224, 80),
                (80, 160, 40),
                (250, 255, 105),
                (240, 250, 0),
                (130.25, 175.5, 22.75),
                (255, 255, 255),
                (0, 0, 0),
            ]:
                for site, channels, diff, coefficient in e.TEXTURE_SITES:
                    encoded = struct.unpack_from(">I", image, site)[0]
                    delta = encoded & 0x3FFFFFC
                    if delta & 0x2000000:
                        delta -= 0x4000000
                    pc = site + delta
                    self.assertEqual(encoded & 3, 0)
                    floats = [42.125 + i for i in range(32)]
                    regs = [0x80000000 + i * 0x1000 for i in range(32)]
                    for index, value in zip(channels, rgb):
                        floats[index] = float(value)
                    oldfloats = floats[:]
                    oldregs = regs[:]
                    captured = None
                    steps = 0
                    while pc != site + 4:
                        steps += 1
                        self.assertLessEqual(steps, 10)
                        w = struct.unpack_from(">I", image, pc)[0]
                        op, fd, fa, fb = w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31
                        if op == 15:
                            regs[fd] = (w & 65535) << 16
                        elif op == 48:
                            imm = w & 65535
                            if imm & 32768:
                                imm -= 65536
                            floats[fd] = struct.unpack_from(
                                ">f", image, regs[fa] + imm - 0x98000000
                            )[0]
                        elif op == 59 and ((w >> 1) & 31) == 20:
                            floats[fd] = f32(floats[fa] - floats[fb])
                        elif op == 59 and ((w >> 1) & 31) == 29:
                            fc = (w >> 6) & 31
                            floats[fd] = f32(floats[fa] * floats[fc] + floats[fb])
                        elif op == 63 and ((w >> 1) & 1023) == 815:
                            captured = [floats[c] for c in channels]
                            floats[fd] = int(floats[fb])
                        elif op == 18:
                            self.assertEqual(w & 3, 0)
                            d = w & 0x3FFFFFC
                            if d & 0x2000000:
                                d -= 0x4000000
                            pc += d
                            continue
                        else:
                            self.fail("Unexpected texture-hook opcode")
                        pc += 4
                    self.assertEqual(steps, 10)
                    expected = [f32(rgb[2] + (rgb[1] - rgb[2]) * f32(c)) for c in tint]
                    self.assertEqual(captured, expected)
                    for i in range(32):
                        if i not in set(channels) | {
                            diff,
                            coefficient,
                            6 if site == 0x2046C else 11,
                        }:
                            self.assertEqual(floats[i], oldfloats[i])
                        if i != 12:
                            self.assertEqual(regs[i], oldregs[i])
                    self.assertEqual(floats[13], oldfloats[13])  # alpha in second generator
                    if tint == [0.0, 0.5, 1.0] and rgb[1] > rgb[2]:
                        self.assertGreater(captured[2], captured[1])
                        self.assertGreater(captured[1], captured[0])
                    if rgb[0] == rgb[1] == rgb[2]:
                        self.assertEqual(captured, list(rgb))
            self.assertEqual(image[0xC58:0xD60], IMAGE[0xC58:0xD60])
        corrupted = bytearray(IMAGE)
        corrupted[0x2046C] ^= 1
        with self.assertRaises(ValueError):
            e.patch(corrupted, p)

    def test_blue_texture_export_roundtrip(self):
        p = e.profile_preset("blue", b.preset("blue"))
        self.assertEqual(p["texture_tint"], [0.0, 0.5, 1.0])
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "bootanim.xex"
            r = b.build(b.DEFAULT_INPUT, target, TOOL, p["effects"], "hdd", False, p)
            self.assertTrue(r["roundtrip_equal"])
            self.assertEqual(r["procedural_texture_hooks"], ["0x2046c", "0x20930"])
            self.assertEqual(r["ribbon_vertex_hooks"], ["0x1b510", "0x1bb08"])
            extracted = Path(td) / "result.image"
            b.run_tool(TOOL, "-b", extracted, target)
            actual = extracted.read_bytes()
            self.assertEqual(actual[0x7A000:], IMAGE[0x7A000:])
            for site, _, _, _ in e.TEXTURE_SITES:
                self.assertEqual(struct.unpack_from(">I", actual, site)[0] >> 26, 18)
        old = e.defaults()
        old.pop("texture_tint")
        self.assertIsNone(e.validate(old)["texture_tint"])

    def test_full_native_ribbon_generator_early_and_curve_phases(self):
        from ribbon_replay import replay

        p = e.defaults()
        p["ribbon_tint"] = [0.0, 0.5, 1.0]
        image, allowed, _ = e.patch(IMAGE, p)
        self.assertTrue({i for i, (a, b) in enumerate(zip(IMAGE, image)) if a != b} <= allowed)
        for time in (0.0, 0.5, 1.99, 2.0, 2.5, 5.0):
            for typ in (-1, 0, 1, 2):
                baseline, oldhits = replay(IMAGE, typ, time, [0.2, 0.9, 0.1])
                result, hits = replay(image, typ, time, [0.2, 0.9, 0.1])
                old = struct.unpack(">5460f", baseline)
                new = struct.unpack(">5460f", result)
                self.assertEqual(hits.get(0x9801B510, 0) + hits.get(0x9801BB08, 0), 130)
                for v in range(780):
                    for component in (0, 1, 2, 6):
                        self.assertEqual(old[v * 7 + component], new[v * 7 + component])
                    r, g, b = new[v * 7 + 3 : v * 7 + 6]
                    self.assertGreater(b, g)
                    self.assertGreater(g, r)
                    self.assertAlmostEqual(g, (r + b) / 2, places=6)
                # Every original path was executed with the same native loop count.
                self.assertEqual(oldhits[0x9801BEF8], hits[0x9801BEF8])
        for rgb in (
            [0.22, 0.58, 0.94],
            [0.0, 0.5, 1.0],
            [0.3, 0.3, 0.3],
            [1.0, 1.0, 1.0],
            [0.0, 0.0, 0.0],
            [0.9, 0.2, 0.1],
        ):
            baseline, _ = replay(IMAGE, -1, 2.5, rgb)
            result, _ = replay(image, -1, 2.5, rgb)
            self.assertEqual(result, baseline)  # No second tint of blue, gray, white or red.
        malformed = bytearray(IMAGE)
        malformed[e.RIBBON_SITES[0]] ^= 1
        with self.assertRaises(ValueError):
            e.patch(malformed, p)
        legacy = e.defaults()
        legacy.pop("ribbon_tint")
        self.assertIsNone(e.validate(legacy)["ribbon_tint"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
