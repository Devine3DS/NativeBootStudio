# Native Boot Studio

A Windows editor for recoloring the modern, native Xbox 360 boot animation. Create a coordinated theme, preview it, and export a complete `bootanim.xex` for your existing RGH/JTAG setup.

[Deutsch](README.de.md) · [User guide](docs/QUICKSTART.en.md) · [HDD/NAND installation](docs/INSTALLATION.en.md) · [Build from source](docs/BUILD.en.md) · [Publish on GitHub](docs/PUBLISHING.en.md)

![Your own preset library](docs/assets/preset-library.png)

## Features

- 40 coordinated color presets, including dark backgrounds.
- Individual colors for the background, swirl, sphere X, glow, highlights, scene tint, and XBOX lettering.
- Save, rename, replace, delete, import, and export your own color presets.
- Adjust the supported size, position, and animation speed settings.
- Optional shader preview using the original animation in Xenia, with playback controls and comparison with the original.
- English and German interface, undo/redo, and saved projects.
- Export a complete XEX for an existing native HDD loader or a NAND image workflow.

This edits the supported modern animation. It does not create arbitrary new motion, replace lettering with custom text, or support the classic boot animation. It does not install or flash anything to a console.

## Getting started

1. Download the **Windows-x64 ZIP** from this repository's Releases page.
2. Extract it into a writable folder and start `NativeBootStudio.exe`.
3. In **Files**, select your own original modern `bootanim.xex` from dashboard/kernel **17559**, and your own **XexTool 6.3**.
4. Optionally select `xenia.exe` for the shader preview. The [tested official Xenia release](https://github.com/xenia-project/release-builds-windows/releases/tag/v1.0.2844-master) is a separate download.
5. Verify the input, choose a preset, customize it, and export.

The public package includes the application, instructions, and its runtime license notices. **Microsoft boot files, XexTool, and Xenia are supplied separately by the user.** See [distribution notes](docs/DISTRIBUTION.en.md).

Use **My presets** to keep or share colors as `.nbpalette.json` files. Back up your `UserPresets` folder before replacing the application folder. Projects use `.nbstudio.json` and can contain paths to files on your own PC.

## Preview and export

The shader preview executes the original renderer in an emulator. The model preview is an approximation. Emulation does not guarantee exactly the same result on hardware; final behavior and altered animation/audio timing need console testing. The preview omits the normal boot audio/handoff.

An HDD export requires an already configured native HDD loader. A NAND export produces an XEX for your existing image-building workflow, not a complete NAND image. Keep the original file and a working recovery backup. Modified XEX files require an appropriate RGH/JTAG console.

## Source layout

| Folder | Contents |
| --- | --- |
| `src/` | Application, color patching, preview, translation, and preset storage |
| `tests/` | Unit tests and optional private-input integration tests |
| `scripts/` | Windows build and clean ZIP packaging |
| `docs/` | English/German guides and release notes |
| `licenses/` | Notices for dependencies in the frozen Windows executable |

Run `python src/studio.py` after installing `requirements.txt`. See the [build guide](docs/BUILD.en.md) for tests and release packaging, [validation](docs/VALIDATION.md) for tested behavior, and [preview implementation](GPU-Preview-Implementation.md) for technical details.

## License and credits

The Native Boot Studio source is available under the [MIT license](LICENSE). This license does not grant rights to Xbox software, XexTool, or Xenia. Runtime and third-party details are in [NOTICE.md](NOTICE.md).

XexTool is by xorloser; Xenia is an independent emulator project. This project is not affiliated with or endorsed by Microsoft, xorloser, or the Xenia team. [Changelog](CHANGELOG.md).
