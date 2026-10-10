# Native Boot Studio — user guide

## Setup

Extract the complete Windows release into a writable folder. Launch `NativeBootStudio.exe`; Python does not need to be installed. Choose English or German in the header.

The public release contains no Microsoft boot files, XexTool, or emulator. On first launch, the **Files** tab explains what to select:

1. Your own **unmodified modern `bootanim.xex` from dashboard/kernel 17559**. An already recolored file or the classic animation is not a supported source.
2. Your own **XexTool 6.3**, used to read and export the XEX.
3. Optionally, **Xenia** for the native shader preview. Use the [tested official Windows release](https://github.com/xenia-project/release-builds-windows/releases/tag/v1.0.2844-master), extract its complete download separately, and select `xenia.exe`. The preview requires a compatible 64-bit Windows PC and graphics driver with Direct3D 12 support.

Click **Check files again**. Export stays disabled until the source is verified. The application remembers verified input/tool paths and your selected Xenia path in `settings.json` beside the EXE.

Alternatively, the default locations are `originals/modern/bootanim.xex`, `tools/xextool.exe`, and `tools/preview/xenia.exe` beside the EXE. These folders are optional and are not included in the public release. Keep any files you supply private unless their terms explicitly allow redistribution.

## Create a theme

Select a preset group and preset under **Palette**. Presets coordinate the background, swirl, sphere X, glow, highlights, scene tint, and lettering. The main color control recolors the related elements while retaining their shading. Individual color controls let you refine the theme.

Use **Details** and **Animation** for the supported layout and timing changes. These adjust the existing animation; custom text and arbitrary new motion are not supported. Native camera controls are available only where the actual preview can use them. Model-only controls are hidden in shader mode.

Use the original comparison and undo/redo to review changes. Preview help can be expanded when needed. The shader preview may briefly restart when a change is applied. Its boot audio/system handoff is omitted; emulation and altered audio timing still need a final check on hardware. The model preview is approximate and remains available without Xenia.

## Your presets and projects

Open **My presets** to save the current colors with a name. Select a saved preset to apply, rename, replace, delete, or export it. Import shared `.nbpalette.json` files through the same library.

Color presets do not change size, position, or animation speed. Built-in presets remain separate from your own saved presets. Your library lives in `UserPresets` beside the EXE: back up that folder when updating.

Save a `.nbstudio.json` project to keep the wider editor settings. Projects can contain your local input/tool paths; inspect them before sharing. Share color preset JSON rather than original or modified Microsoft XEX files.

## Export

Choose the target when exporting `bootanim.xex`:

- **HDD:** creates a file for a native HDD loader. With `remap_bootanim_17559`, place it at the root of the internal HDD as `Hdd:\bootanim.xex`; the remap is applied to the NAND image once.
- **NAND:** creates a file to replace `bootanim.xex` in a rebuilt NAND image, using its actual CRC-32 and a build without the HDD remap. It is not a complete NAND image.

The included [installation guide](INSTALLATION.en.md) explains both routes, the separate remap download, xeBuild/J-Runner setup, RGH3 handling, and direct NAND replacement. In the Windows release, that guide is under `docs/INSTALLATION.en.md`.

The application verifies the resulting file and writes an export report. It does not copy files to the console or flash a NAND. Keep your original file and a known working recovery backup. These exports require a suitable RGH/JTAG console; an unmodified retail console cannot run them.

Animation speed changes do not retime the original audio. Confirm the final appearance, timing, and boot behavior on your console.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Export disabled | Select the original file and XexTool, then verify the input. |
| Source rejected | Use the supported, unmodified modern 17559 original. |
| Shader preview unavailable | Select Xenia and check its Windows/GPU requirements. |
| Cannot save settings/presets | Move the extracted folder to a writable location. |
| A preset name already exists | Rename it or explicitly replace that preset. |

See `LICENSE` and `NOTICE.md` in this package for licensing. Third-party tools and Xbox files remain subject to their own terms.
