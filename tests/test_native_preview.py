import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import native_preview as gpu
import native_boot_color as backend
import palettes
from test_studio import IMAGE, RAW_XEX

RAW = RAW_XEX


@unittest.skipUnless(RAW is not None, "Supply your own original XEX and XexTool for adapter tests")
class NativePreviewTests(unittest.TestCase):
    def test_preview_adapter_retains_shaders_audio_and_console_export_separation(self):
        from native_extension import patch

        for name in ("original", "black_blue", "sunset"):
            profile = palettes.palette(name)
            before = bytes(RAW)
            adapted = gpu.prepare(RAW, profile, 3.0)
            payload = backend.word(adapted, 8)
            actual = adapted[payload : payload + len(IMAGE)]
            expected, _, _ = patch(IMAGE, profile)
            changed = {i for i, (a, b) in enumerate(zip(expected, actual)) if a != b}
            allowed = set(range(gpu.ENTRY, gpu.ENTRY + 0x100)) | set(
                range(gpu.CONTROL, gpu.CONTROL + 32)
            )
            allowed |= set(range(0xFF68, 0xFF70)) | set(range(0xEA38, 0xEA3C))
            self.assertTrue(changed <= allowed)
            self.assertEqual(actual[0x7A000:], expected[0x7A000:])
            self.assertEqual(actual[gpu.CONTROL + 16 : gpu.CONTROL + 24], gpu.MARKER)
            self.assertEqual(backend.word(adapted, 4), 1)
            with self.assertRaises(ValueError):
                backend.read_uncompressed(adapted)
            self.assertEqual(RAW, before)

    def test_clock_hook_decodes_to_absolute_native_time_and_writable_controls(self):
        from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN

        data = gpu.prepare(RAW, palettes.palette("blue"), 7.0)
        payload = backend.word(data, 8)
        image = data[payload:]
        code = list(
            Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN).disasm(
                image[gpu.CLOCK : gpu.CLOCK + 44], 0x98000000 + gpu.CLOCK
            )
        )
        self.assertEqual(len(code), 11)
        self.assertEqual(
            [i.mnemonic for i in code],
            ["lis", "lfs", "stfs", "lfs", "lfs", "stfs", "lwz", "addi", "lis", "stw", "b"],
        )
        self.assertEqual(code[-1].op_str, "0x9800ea3c")
        self.assertEqual(struct.unpack_from(">4f", image, gpu.CONTROL), (7.0, 0.0, 0.0, 1.0))
        # PC control storage is in writable native .data, away from GPU code.
        self.assertGreater(gpu.CONTROL, 0x77500)
        self.assertLess(gpu.CONTROL + 32, 0x7A000)

    def test_unknown_source_rejected_before_preview_adapter(self):
        wrong = bytearray(RAW)
        wrong[backend.word(RAW, 8) + 0x2600] ^= 1
        with self.assertRaises(ValueError):
            gpu.prepare(wrong, palettes.palette("blue"))


if __name__ == "__main__":
    unittest.main()
