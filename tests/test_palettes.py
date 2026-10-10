import copy
from pathlib import Path
import random
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import native_extension as e
import native_boot_color as b
import palettes
import scene
from test_studio import IMAGE


def background_shader(image, position, fade, rgb):
    """Execute the actual ADD/MAX/MAD/MUL ALUs using Xenia ucode.h bitfields.

    Restricted to this straight-line shader; no rasterizer or GPU emulation.
    """
    registers = [[0.0, 0.0, 0.0, 0.0] for _ in range(2)]
    registers[0] = list(position)
    constants = {0: [fade, *rgb], 255: list(struct.unpack_from(">4f", image, 0x2518))}
    words = struct.unpack_from(">3I", image, 0x2528)
    cf = (words[2] << 16) | (words[1] >> 16)
    assert (cf >> 44) & 15 == 2  # EXEC_END
    address = cf & 4095
    count = (cf >> 12) & 7
    assert address == 1 and count in (5, 6)
    output = [None] * 4
    for offset in range(0x2528 + address * 12, 0x2528 + (address + count) * 12, 12):
        a, bits, c = struct.unpack_from(">3I", image, offset)
        sources = []
        for index, shift in ((1, 16), (2, 8), (3, 0)):
            register = (c >> shift) & 255
            if c & (1 << (32 - index)):
                assert (register & 63) < 2 and not register & 64
                source = list(registers[register & 63])
                if register & 128:
                    source = [abs(v) for v in source]
            else:
                source = list(constants[register])
            swizzle = (bits >> shift) & 255
            source = [source[((swizzle >> (i * 2)) + i) & 3] for i in range(4)]
            if bits & (1 << (27 - index)):
                source = [-v for v in source]
            sources.append(source)
        opcode = (c >> 24) & 31
        if opcode == 0:
            vector = [x + y for x, y in zip(sources[0], sources[1])]
        elif opcode == 1:
            vector = [x * y for x, y in zip(sources[0], sources[1])]
        elif opcode == 11:
            vector = [x * y + z for x, y, z in zip(*sources)]
        else:
            raise AssertionError(opcode)
        scalar_opcode = a >> 26
        if scalar_opcode == 2:
            scalar = max(sources[2][3], sources[2][0])
        else:
            assert scalar_opcode == 50
            scalar = None
        vm, sm = (a >> 16) & 15, (a >> 20) & 15
        if a & (1 << 15):
            for i in range(4):
                v, s = bool(vm & (1 << i)), bool(sm & (1 << i))
                if v and s:
                    output[i] = 1.0
                elif v:
                    output[i] = vector[i]
                elif s:
                    output[i] = scalar
                elif a & (1 << 14):
                    output[i] = 0.0
        else:
            vd, sd = a & 63, (a >> 8) & 63
            for i in range(4):
                if vm & (1 << i):
                    registers[vd][i] = vector[i]
                if sm & (1 << i):
                    registers[sd][i] = scalar
    return output


class PaletteTests(unittest.TestCase):
    def test_all_40_presets_validate_and_retain_transform_and_speed(self):
        self.assertEqual(len(palettes.PALETTES), 40)
        self.assertEqual(len(palettes.BY_ID), 40)
        self.assertEqual(len(palettes.BY_LABEL), 40)
        original = e.defaults()
        original["animation_speed"] = 1.2
        original["text_transform"] = {"scale": 0.8, "x": 0.1, "y": -0.05}
        for name in palettes.BY_ID:
            with self.subTest(name=name):
                p = palettes.apply(original, name)
                e.validate(p)
                self.assertEqual(p["animation_speed"], 1.2)
                self.assertEqual(p["text_transform"], original["text_transform"])

    @unittest.skipUnless(IMAGE is not None, "Native image not provided")
    def test_all_40_presets_patch_native_image(self):
        for name in palettes.BY_ID:
            p = palettes.palette(name)
            image, allowed, _ = e.patch(IMAGE, p)
            self.assertTrue({i for i, (a, c) in enumerate(zip(IMAGE, image)) if a != c} <= allowed)
            if p["background_color"] is not None:
                self.assertEqual(
                    list(struct.unpack_from(">3f", image, e.BACKGROUND_VALUE)),
                    [struct.unpack(">f", struct.pack(">f", v))[0] for v in p["background_color"]],
                )

    def test_existing_projects_and_classic_presets_keep_original_native_bytes(self):
        old = e.defaults()
        old.pop("background_color")
        self.assertIsNone(e.validate(old)["background_color"])
        for name in ("original", "blue", "cyan", "purple"):
            p = palettes.palette(name)
            previous = e.profile_preset(name, b.preset(name))
            self.assertEqual(p, previous)
        for invalid in ([], [1, 2, 0], [1, 0, float("nan")], [True, 0, 1]):
            p = e.defaults()
            p["background_color"] = invalid
            with self.assertRaises(ValueError):
                e.validate(p)

    @unittest.skipUnless(IMAGE is not None, "Native image not provided")
    def test_actual_background_shader_rgb_and_alpha(self):
        randomizer = random.Random(17559)
        for rgb in ([0, 0, 0], [1, 1, 1], [0.07, 0.12, 0.2], [0.91, 0.1, 0.33], [0, 0.8, 1]):
            p = e.defaults()
            p["background_color"] = rgb
            changed, _, _ = e.patch(IMAGE, p)
            for _ in range(200):
                position = [randomizer.uniform(-2, 2) for _ in range(4)]
                fade = randomizer.uniform(-0.5, 0.5)
                original = background_shader(IMAGE, position, fade, [0, 0, 0])
                actual = background_shader(changed, position, fade, rgb)
                self.assertEqual(original[3], 1.0)
                self.assertEqual(actual[3], 1.0)
                for i in range(3):
                    self.assertAlmostEqual(actual[i], original[i] * rgb[i], places=10)

    @unittest.skipUnless(IMAGE is not None, "Native image not provided")
    def test_native_background_hook_preserves_gradient_and_other_registers(self):
        p = e.defaults()
        p["background_color"] = [0.1, 0.2, 0.3]
        image, _, _ = e.patch(IMAGE, p)
        registers = [0x90000000 + i * 0x100 for i in range(32)]
        registers[11] = 0x81000000
        before = registers[:]
        floats = [float(i) for i in range(32)]
        oldfloats = floats[:]
        writes = {}
        pc = e.BACKGROUND_CODE
        while pc < e.BACKGROUND_CODE + 36:
            word = struct.unpack_from(">I", image, pc)[0]
            op = word >> 26
            rt, ra = (word >> 21) & 31, (word >> 16) & 31
            imm = word & 65535
            imm = imm - 65536 if imm & 32768 else imm
            if op == 15:
                registers[rt] = (imm << 16) & 0xFFFFFFFF
            elif op == 48:
                address = (registers[ra] + imm) & 0xFFFFFFFF
                floats[rt] = struct.unpack_from(">f", image, address - 0x98000000)[0]
            elif op == 52:
                writes[registers[ra] + imm] = floats[rt]
            elif op == 18:
                delta = word & 0x3FFFFFC
                if delta & 0x2000000:
                    delta -= 0x4000000
                self.assertEqual(pc + delta, e.BACKGROUND_SITE + 4)
                break
            else:
                raise AssertionError(hex(word))
            pc += 4
        self.assertEqual(
            set(writes), {before[11] + 0x1784, before[11] + 0x1788, before[11] + 0x178C}
        )
        for i, v in enumerate(p["background_color"]):
            self.assertAlmostEqual(writes[before[11] + 0x1784 + 4 * i], v, places=6)
        for i in range(32):
            if i != 12:
                self.assertEqual(registers[i], before[i])
                self.assertEqual(floats[i], oldfloats[i])
        self.assertNotIn(before[11] + 0x1780, writes)  # Animated grayscale/fade retained.

    @unittest.skipUnless(IMAGE is not None, "Native image not provided")
    def test_black_background_export_both_targets_and_old_blue_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            hashes = []
            for mode in ("hdd", "flash"):
                p = palettes.palette("black_blue")
                target = Path(directory) / (mode + ".xex")
                report = b.build(
                    b.DEFAULT_INPUT, target, b.find_tool(), p["effects"], mode, False, p
                )
                hashes.append(report["output_image_sha256"])
                self.assertEqual(report["background_hook"], "0x11ef0")
                self.assertEqual(report["background_color"], [0, 0, 0])
                self.assertTrue(report["roundtrip_equal"])
                self.assertTrue(report["audio_unchanged"])
                self.assertTrue(report["media_bindings_verified"])
            self.assertEqual(*hashes)

    @unittest.skipUnless(IMAGE is not None, "Native image not provided")
    def test_preview_background_and_original_comparison(self):
        from test_studio import IMAGE

        model = scene.extract(IMAGE)
        p = palettes.palette("black_blue")
        rendered = scene.render_view(model, p, (500, 300))
        self.assertEqual(rendered.getpixel((0, 0)), (0, 0, 0))
        compared = scene.render_view(model, p, (800, 400), compare=True)
        self.assertEqual(compared.getpixel((0, 31)), (245, 245, 245))
        self.assertEqual(compared.getpixel((799, 31)), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
