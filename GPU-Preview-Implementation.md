# Native preview implementation and limitations

The bootanim is a DLL with exports at 98020e60 / 98020ec8 / 98020ed8 and no
title entry point. The PC adapter adds an inline XEX entry (10100) and changes
module flags only in a temporary copy. Image base remains 98000000.

Entry at 58a00 invokes export 1 with flag 8000 (synchronous mode). The missing
Xenia VdTurnDisplayOff call at ff68 is omitted. A setup trampoline at 58a40
sets the context draw flag (19) before the original loop. This bypasses the
boot audio thread, which did not launch reliably as a normal title.

A hook at ea38 supplies the selected absolute native animation time and zero
frame delta. The original ea10 update invokes camera 12338 and scene 1f298;
original fb30 renders the shaders and postprocess. The editor never renders
a substitute mesh in native mode. Controls and frame counter are at 79f00,
in writable .data; initial code-page storage caused a write fault and was
moved. Preview code uses a separate verified zero area at 58a00..58aff and
does not overlap console-export patches. The full console image is compared
in tests to ensure only documented preview offsets differ.

The editor owns one child Xenia process. It finds only that child's window,
embeds it in its canvas and resizes it on actual layout changes. Its private
guest mapping is recognized by an exact NBSGPU41 marker at the known control
address in Xenia's power-of-two guest-memory mapping. Only two float controls
are written through that child process handle. No other processes are read.

Color changes rebuild the temporary preview after a 550 ms debounce, since
procedural textures are generated at native initialization. Timeline updates
write the time control without rebuilding. Original palette comparison uses
the same renderer. CPU viewer and gallery remain explicitly approximate.

This is native-renderer emulation, not verified console pixel equivalence.
Absolute seeking suppresses incremental frame delta; boot handoff flags,
audio, display-off behavior and dashboard transition are omitted. These
changes are confined to the PC adapter. Temporal effects and seek history may
still differ from uninterrupted console playback. Further validation needs
console capture comparison at matching times, including MSAA, gamma and fade.
The preview does not prove console stability of every edited palette.

Reproducibility: src/native_preview.py and tests/test_native_preview.py.
Integration tests require user-supplied private inputs; the public repository
contains neither a Microsoft XEX nor an emulator binary. The tested upstream
Xenia build is v1.0.2844-master (commit 95a5c3ee2). Users select their own
xenia.exe in Files or through NBS_XENIA. Xenia's own license and dependency
notices apply separately.

The adapter is generated in a temporary directory for PC preview only. It is
never used as the console export. Public archives contain the editor and its
runtime notices; all Xbox files and external tool binaries are excluded.
