# Native Boot Studio

Customize the colors of the modern Xbox 360 boot animation, preview your theme on your PC, and export `bootanim.xex` for your RGH/JTAG console.

**[Download for Windows](https://github.com/Devine3DS/NativeBootStudio/releases/latest)** · **[Deutsche Anleitung](README.de.md)**

![Native Boot Studio editor with the Blue on Black theme in the native shader preview](docs/assets/editor-shader-blue.png)

*Blue on Black in Native Boot Studio 4.2.2, using the native shader preview through Xenia.*

This tutorial takes you from the first launch to installing your animation. The supported source is the **modern boot animation from dashboard/kernel 17559**. The classic animation is not supported.

## 1. Download and set up

You need:

- A Windows x64 PC and the **Windows-x64 ZIP** from the download link above. You do not need to install Python.
- Your own **unmodified modern 17559 `bootanim.xex`**.
- **XexTool 6.3** to read and export the animation.
- Optional: [Xenia for Windows](https://github.com/xenia-project/release-builds-windows/releases/tag/v1.0.2844-master) for the shader preview. This requires a compatible GPU/driver with Direct3D 12 support.
- An Xbox 360 with RGH/JTAG and dashboard **17559** to use the exported animation.

The Windows download contains Native Boot Studio and its instructions. The original Xbox file, XexTool, and Xenia must be provided separately.

1. Download **NativeBootStudio-4.2.2-Windows-x64.zip** from [Releases](https://github.com/Devine3DS/NativeBootStudio/releases/latest).
2. Extract the entire ZIP into a folder where you can save files, then run `NativeBootStudio.exe`.
3. Choose **English** or **Deutsch** at the top of the window.
4. Open **Files** and select your original `bootanim.xex` and `xextool.exe`.
5. If you want the shader preview, extract the complete Xenia download into a separate folder and select its `xenia.exe` in **Files**.
6. Click **Check files again**. Once the check succeeds, the editor is ready to export. It remembers the selected file paths for the next launch.

Use an untouched original as the input; do not select a previously exported theme as the source.

<details>
<summary>Screenshot: first launch and file setup</summary>

![Files tab before selecting the original animation, XexTool, and optional Xenia](docs/assets/file-setup.png)

The Files tab shows filenames only once selected, keeping Windows usernames and folder paths out of the interface.

</details>

## 2. Create your color theme

1. Open **Palette**, choose a preset group, then select one of the 40 presets. For a blue animation on a black background, choose **Dark → Blue on Black**.
2. Click the large color swatch below the preset controls to change the swirl, sphere X, glow, and XBOX lettering together.
3. Refine individual colors below it: **Background**, **Swirl color**, **Sphere X**, **Glow**, **Highlights**, **Scene tint**, and **XBOX text**. Use **Details** for additional effects and lighting colors.
4. Use the supported controls in **Details** and **Animation** to adjust layout and animation speed.
5. Replay the animation and compare it with the original. Undo/redo lets you step back through your edits.

![Built-in preset gallery with different color themes](docs/assets/preset-gallery.png)

*Browse 40 built-in palettes. Gallery thumbnails use the model preview with approximate lighting.*

With Xenia configured, click **Start shader preview** to view the original renderer, shaders, textures, and camera movement with your settings. Without Xenia, you can use the model preview, which approximates the animation. The shader preview may restart briefly after edits. Check the finished result on your console: emulator output can differ from hardware, and changing animation speed does not retime the boot audio.

<details>
<summary>Screenshot: Gold on Black in the native shader preview</summary>

![Gold on Black theme with individual color controls and native shader preview](docs/assets/editor-shader-gold.png)

The same animation with a coordinated gold palette and black background, rendered through Xenia.

</details>

The editor changes the existing animation. Custom replacement text and entirely new animation sequences are not available.

### Save your own presets

Open **My presets** and save the current colors with a name. You can apply, rename, replace, delete, import, or export saved presets there. Shared color presets use `.nbpalette.json` files.

Presets contain colors; size, position, and speed stay as they are. Save a `.nbstudio.json` project to keep the wider editor settings. Back up the `UserPresets` folder beside the EXE before updating the application.

![Custom preset library](docs/assets/preset-library.png)

*Example saved palettes in My presets, with controls for applying, renaming, replacing, and sharing them.*

## 3. Export bootanim.xex

Click **Export bootanim.xex …**, choose the destination, and select the target that matches how your console will load the file:

| Target | Where the console loads the animation | Installation |
| --- | --- | --- |
| **HDD** | Root of the internal hard drive: `Hdd:\bootanim.xex` | Install the HDD remap in the NAND image once. |
| **NAND** | Flash filesystem inside the NAND image | Rebuild your NAND image with the exported XEX and its CRC-32. |

Name the export **`bootanim.xex`** and wait for the successful verification message. **Open export folder** shows the file and its report. A saved project or a preset JSON is for the PC editor; the console uses the exported XEX.

Native Boot Studio exports the animation file. Use your existing console tools to copy the HDD file or build and flash the NAND image as described below. Before changing a NAND image, back up your working NAND dump, CPU key, original boot file, and image-builder settings. Use the board, NAND, and hack settings already verified for your console.

## 4A. Install on the internal HDD

The [Xbox360BootAnimationCreator release](https://github.com/TheOnlyLordVirus/Xbox360BootAnimationCreator/releases/tag/Release) supplies `remap_bootanim_17559.bin`, credited there to **Mena**. The patch is a separate download, not part of this release.

1. Export your theme from Native Boot Studio with target **HDD**, naming the file `bootanim.xex`.
2. Back up an existing HDD boot file, then copy the export to the **root of the internal HDD**, shown as `Hdd:\bootanim.xex` or `Hdd1:\bootanim.xex` in common file managers. A USB drive or a subfolder is not the documented target of this remap.
3. If this exact remap is already installed and loading that path, no new NAND build is needed to change themes: replace the HDD file and reboot.
4. Otherwise download **only the remap asset** from the linked release. Put it in `xeBuild\17559\bin\remap_bootanim_17559.bin` inside your separate xeBuild/J-Runner installation.
5. Load your own NAND and CPU key in your image builder and keep its correct board/hack settings. Add this patch argument to the build command:

   ```text
   -a remap_bootanim_17559
   ```

   The argument uses the patch name **without `.bin`**. Keep the rest of your working command and the required RGH3 conversion steps. The release author's Xenon/JTAG example is not a command for a Corona/RGH3 console.
6. In J-Runner with Extras, a custom command can be entered under **Advanced → XeBuild Command…**. That dialog accepts xeBuild arguments, not `xeBuild.exe`; J-Runner supplies its data/output paths, so omit `-d` and the output filename. Keep all relevant flags from your existing setup. **For RGH3, this custom-command route must not be assumed to run the normal automatic RGH3 post-build conversion. Load the built image as the source and complete conversion through Advanced → Convert to RGH3, using your correct board/CPU key and established settings, before flashing.**
7. Review the successful build log for the remap and verify the finished image belongs to your console and still has the correct hack type. Flash the completed image using the method appropriate to your board/NAND, then reboot with the internal HDD connected.

Once installed, further color changes only require a new **HDD** export and replacement of `Hdd:\bootanim.xex`. Do not assume the remap falls back to the NAND animation when that HDD/file is absent.

## 4B. Install directly in the NAND

Use this route to keep the animation in the NAND. It must use the normal NAND boot path, **without `remap_bootanim_17559`**. Replacing a NAND file while the kernel still redirects to the HDD will not select that NAND animation.

1. Export from Native Boot Studio with target **NAND**, naming the file `bootanim.xex`.
2. Work in a backed-up copy of your xeBuild/J-Runner setup. Load your own NAND dump/CPU key and select your correct console settings and dashboard **17559**.
3. Place the exported XEX at `xeBuild\17559\bootanim.xex` in that builder copy.
4. Find the firmware INI actually used by the build. For a standard 17559 Glitch2 build, it is `xeBuild\17559\_glitch2.ini`; JTAG uses `_jtag.ini`. Alternative build profiles can select a different INI, so check the build log.
5. In its `[flashfs]` section, replace only the `bootanim.xex` entry's CRC-32 with the CRC of **your exported NAND file**. Leave all other entries and sections intact. The format is:

   ```ini
   bootanim.xex,YOUR_8_DIGIT_CRC32
   ```

   `YOUR_8_DIGIT_CRC32` is a placeholder, not a value to copy. The included read-only helper calculates it in PowerShell, without modifying the file:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\crc32.ps1 -Path 'C:\MyExports\bootanim.xex'
   ```

   Run this from the extracted application/source root. The execution-policy argument applies only to this helper process. Copy its eight hexadecimal digits into the INI. CRC-32 is different from the SHA-256 shown in Studio's report. Recalculate it after every new export.
6. Build the NAND image through your normal workflow, keeping the required RGH3 steps and **not adding the remap argument**. Check that the log uses your replacement file with its matching CRC and completes successfully. If it selects the stock file, reports a CRC mismatch, or runs out of filesystem space, do not flash it; correct the input/profile first.
7. Restore your builder's original INI/file after the custom build, so future images do not accidentally inherit the theme. Verify the resulting image for your console, flash it through your established board-specific method, and reboot.

The file is replaced in a newly built NAND **image**. Do not hex-patch an assumed raw offset or delete the live `Flash:`/`SFC:` boot file in a dashboard file manager as a substitute for rebuilding the filesystem.

## Switching routes and checking the result

- **HDD → NAND:** build an image without the remap and include the NAND export with its correct CRC. Leaving the HDD file in place does not make the kernel stop redirecting there.
- **NAND → HDD:** use an HDD export and apply the remap as in section 4A.
- If the stock animation still appears, check the actual boot path, export target, active firmware INI, build log, and filename before changing colors again.

## Troubleshooting

| Problem | Solution |
| --- | --- |
| Export is disabled | Select the original XEX and XexTool in **Files**, then click **Check files again**. |
| The original file is rejected | Use an unmodified modern 17559 original, rather than the classic animation or an existing theme. |
| Shader preview will not start | Select the extracted `xenia.exe` and check Windows/GPU/Direct3D 12 support. You can still use the model preview. |
| Settings or presets cannot be saved | Extract the application into a writable folder and run it from there. |
| The console still shows the old animation | Check the export target, actual boot path, HDD filename, or the NAND build's active INI and CRC. |
| Animation and sound finish at different times | Return animation speed towards the original setting; the audio is not retimed. |

More details: [Editor guide](docs/QUICKSTART.en.md) · [Installation guide](docs/INSTALLATION.en.md).

## License and credits

Native Boot Studio is licensed under [MIT](LICENSE). Xbox boot files and external tools retain their own terms; see [NOTICE.md](NOTICE.md). XexTool is by xorloser, Xenia is an independent emulator project, and the linked HDD remap is credited to Mena. This project is not affiliated with Microsoft.
