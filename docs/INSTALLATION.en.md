# Install an exported boot animation

[Deutsch](INSTALLATION.de.md)

Choose one of these routes for a supported **17559 RGH/JTAG console**:

| Route | Studio export target | Where the animation is stored | NAND change |
| --- | --- | --- | --- |
| HDD with remap | **HDD** | Root of the internal HDD: `Hdd:\bootanim.xex` | Apply the 17559 remap patch once. |
| Direct NAND replacement | **NAND** | NAND image's flash filesystem as `bootanim.xex` | Rebuild the image with your exported file; omit the remap. |

Native Boot Studio creates the XEX and export report. NAND building/flashing is performed separately. Back up the current working NAND dump, CPU key, original boot file, and builder configuration before changing the image. Use the board/NAND/hack settings already verified for your own console. A Corona 4 GB eMMC and a 16 MB NAND need their respective flashing methods.

## Option A — HDD using remap_bootanim_17559

The [Xbox360BootAnimationCreator release](https://github.com/TheOnlyLordVirus/Xbox360BootAnimationCreator/releases/tag/Release) supplies `remap_bootanim_17559.bin`, credited there to **Mena**. We use that patch's documented HDD installation method; Native Boot Studio still creates the animation itself. The patch is a separate download, not part of this release.

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

## Option B — Replace bootanim.xex in a rebuilt NAND image

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
- **NAND → HDD:** use an HDD export and apply the remap as in Option A.
- If the stock animation still appears, check the actual boot path, export target, active firmware INI, build log, and filename before changing colors again.

These installation instructions are based on the upstream remap release, J-Runner's command handling, and its 17559 firmware configuration. Local tests verify Studio's XEX export, not NAND flashing or this patch on every board. Preserve a working recovery route before flashing.

Sources: [remap instructions and download](https://github.com/TheOnlyLordVirus/Xbox360BootAnimationCreator/releases/tag/Release), [J-Runner source](https://github.com/Octal450/J-Runner-with-Extras), and the official package linked from its README (17559 firmware INI/readme). External files retain their own licensing terms.
