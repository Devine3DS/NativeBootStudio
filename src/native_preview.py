"""PC-only Xenia adapter. Never used by the console export path.

Runs the original boot renderer synchronously, without the boot audio thread or
display-off call. The editor supplies absolute animation time to the native
camera and geometry update. Xenos shaders, textures and draw code remain native.
"""

import ctypes
from ctypes import wintypes as w
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import time
import native_boot_color as backend
from native_extension import patch
from i18n import app_dir, load_preferences

ENTRY = 0x58A00
SETUP = 0x58A40
CLOCK = 0x58A80
CONTROL = 0x79F00
MARKER = b"NBSGPU41"


def branch(site, destination, link=False):
    return 0x48000000 | ((destination - site) & 0x3FFFFFC) | int(link)


def prepare(raw, profile, time=0.0):
    payload, original = backend.read_uncompressed(raw)
    backend.verify_hook_pages(raw)
    image, _, _ = patch(original, profile)
    assert not any(image[ENTRY : ENTRY + 0x100]), "Preview code overlaps console patches"
    assert not any(image[CONTROL : CONTROL + 32]), "Preview controls overlap native data"
    xex = bytearray(raw)
    count = backend.word(xex, 20)
    if 24 + 8 * (count + 1) > backend.word(xex, 16):
        raise ValueError("No room for the PC preview entry header")
    struct.pack_into(">I", xex, 4, 1)  # executable adapter, original stays a boot DLL
    struct.pack_into(">I", xex, 20, count + 1)
    struct.pack_into(">2I", xex, 24 + 8 * count, 0x10100, 0x98000000 + ENTRY)

    def put(offset, *words):
        struct.pack_into(">" + str(len(words)) + "I", image, offset, *words)

    put(ENTRY, 0x38600000, 0x38800000, 0x60848000, branch(ENTRY + 12, 0x20E60, True), 0x48000000)
    put(0xFF68, 0x60000000)  # omit VdTurnDisplayOff, not implemented by Xenia
    put(0xFF6C, branch(0xFF6C, SETUP))
    put(SETUP, 0x807F9080, 0x39600001, 0x99630019, branch(SETUP + 12, 0xFF70))
    # Replace fmr f31,f1 at EA38. Supply absolute time and zero frame delta.
    # Original EA10 then calls the original camera and ribbon generators.
    put(0xEA38, branch(0xEA38, CLOCK))
    put(
        CLOCK,
        0x3D609808,
        0xC00B9F00,
        0xD01F000C,
        0xC3EB9F04,
        0xC00B9F0C,
        0xD01F0024,
        0x816B9F08,
        0x396B0001,
        0x3D409808,
        0x916A9F08,
        branch(CLOCK + 40, 0xEA3C),
    )
    struct.pack_into(">4f", image, CONTROL, float(time), 0.0, 0.0, max(0.0, float(time) - 6.0))
    image[CONTROL + 16 : CONTROL + 24] = MARKER
    xex[payload : payload + len(image)] = image
    return bytes(xex)


class Session:
    """Owns just the child emulator it launches; embeds its render window."""

    def __init__(self):
        self.executable = Path(
            os.environ.get(
                "NBS_XENIA",
                load_preferences().get("xenia", str(app_dir() / "tools/preview/xenia.exe")),
            )
        )
        self.directory = tempfile.TemporaryDirectory(prefix="NativeBootStudio-GPU-")
        self.folder = Path(self.directory.name)
        self.proc = None
        self.handle = None
        self.hwnd = None
        self.mapping = None
        self.output = None
        self.generation = 0
        self.frames = 0
        self.size = None
        self.started = 0.0
        self.last_check = 0.0

    @property
    def available(self):
        return os.name == "nt" and self.executable.is_file()

    def start(self, data):
        self.stop()
        self.generation += 1
        self.mapping = None
        self.hwnd = None
        self.frames = 0
        self.size = None
        self.started = time.monotonic()
        path = self.folder / f"PC-ONLY-preview-{self.generation}.xex"
        path.write_bytes(data)
        log = self.folder / "preview.log"
        self.output = (self.folder / "stdout.log").open("w", encoding="utf-8")
        self.proc = subprocess.Popen(
            [
                str(self.executable),
                str(path),
                "--headless=false",
                "--gpu=d3d12",
                "--apu=nop",
                "--hid=nop",
                "--discord=false",
                "--storage_root=" + str(self.folder),
                "--log_file=" + str(log),
                "--log_level=1",
            ],
            cwd=self.folder,
            stdout=self.output,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        api = ctypes.windll.kernel32
        api.OpenProcess.restype = w.HANDLE
        self.handle = api.OpenProcess(0x0038 | 0x0400, False, self.proc.pid)

    def read(self, address, size):
        buffer = ctypes.create_string_buffer(size)
        done = ctypes.c_size_t()
        ok = ctypes.windll.kernel32.ReadProcessMemory(
            w.HANDLE(self.handle), ctypes.c_void_p(address), buffer, size, ctypes.byref(done)
        )
        return buffer.raw if ok and done.value == size else None

    def tick(self, parent, width, height, at_time):
        if self.proc is None:
            return "stopped"
        if self.proc.poll() is not None:
            return "failed"
        now = time.monotonic()
        if now - self.last_check > 0.5:
            self.last_check = now
            log = self.folder / "preview.log"
            if log.exists() and "==== CRASH DUMP ====" in log.read_text(errors="replace"):
                return "failed"
        if not self.frames and now - self.started > 25:
            return "failed"
        if self.mapping is None:
            for power in range(32, 64):
                candidate = 1 << power
                if self.read(candidate + 0x98000000 + CONTROL + 16, 8) == MARKER:
                    self.mapping = candidate
                    break
        if self.mapping is not None:
            values = struct.pack(">f", float(at_time))
            done = ctypes.c_size_t()
            address = self.mapping + 0x98000000 + CONTROL
            ctypes.windll.kernel32.WriteProcessMemory(
                w.HANDLE(self.handle), ctypes.c_void_p(address), values, 4, ctypes.byref(done)
            )
            fade = struct.pack(">f", max(0.0, float(at_time) - 6.0))
            ctypes.windll.kernel32.WriteProcessMemory(
                w.HANDLE(self.handle), ctypes.c_void_p(address + 12), fade, 4, ctypes.byref(done)
            )
            frame_data = self.read(address + 8, 4)
            if frame_data:
                self.frames = struct.unpack(">I", frame_data)[0]
        user = ctypes.windll.user32
        if self.hwnd is None:
            windows = []
            callback_type = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)

            @callback_type
            def visit(hwnd, param):
                pid = w.DWORD()
                user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                rect = w.RECT()
                user.GetClientRect(hwnd, ctypes.byref(rect))
                if pid.value == self.proc.pid and rect.right > 500 and rect.bottom > 300:
                    windows.append(hwnd)
                return True

            user.EnumWindows(visit, 0)
            if windows:
                self.hwnd = windows[0]
                user.SetParent.argtypes = [w.HWND, w.HWND]
                user.SetWindowLongPtrW.argtypes = [w.HWND, ctypes.c_int, ctypes.c_ssize_t]
                user.SetWindowLongPtrW(self.hwnd, -16, 0x50000000)  # child, visible
                user.SetMenu(w.HWND(self.hwnd), None)
                user.SetParent(self.hwnd, parent)
        if self.hwnd is not None and self.size != (width, height):
            self.size = (width, height)
            user.MoveWindow(w.HWND(self.hwnd), 0, 0, max(1, width), max(1, height), True)
        return "ready" if self.hwnd and self.frames > 0 else "loading"

    def stop(self):
        if self.proc is not None:
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=3)
            self.proc = None
        if self.handle:
            ctypes.windll.kernel32.CloseHandle(w.HANDLE(self.handle))
            self.handle = None
        if self.output:
            self.output.close()
            self.output = None
        self.hwnd = None
        self.mapping = None
        self.frames = 0

    def close(self):
        self.stop()
        self.directory.cleanup()
