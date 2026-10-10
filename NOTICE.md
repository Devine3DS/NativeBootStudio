# License and dependency notices

The Native Boot Studio source and its own documentation are licensed under MIT; see `LICENSE`. This permission does not extend to separately supplied Xbox files or external tools.

## Windows executable

The frozen executable includes Python, Tcl/Tk, Pillow (and components covered by its bundled notices), and the PyInstaller bootloader. Packaging support is also included in the frozen runtime. The complete upstream notices are provided in `licenses/runtime/`:

- `Python-LICENSE.txt`: Python 3.13 licensing and historical notices.
- `Tcl-license.terms` and `Tk-license.terms`: Tcl/Tk notices.
- `Pillow-LICENSE.txt`: Pillow 11.3.0 and bundled library notices, including FreeType attribution.
- `PyInstaller-COPYING.txt`: PyInstaller 6.20.0, including its bootloader exception.
- `packaging/`: packaging 26.2 licenses (BSD/Apache).

These notices are preserved in the Windows release. A rebuild with different dependencies may require updated notices.

The Windows Python runtime also includes unmodified OpenSSL 3.0.16 (Apache 2.0, included in `Python-LICENSE.txt`), libffi, bzip2, and Microsoft runtime components covered by that file's additional Windows conditions. zlib's notice is also included in the bundled Pillow notices. Python's runtime components are separate from the excluded Xbox software.

## Separately supplied files

The public source and Windows release contain **no Microsoft boot animation, original or modified XEX, NAND image, XexTool, or Xenia binary**.

- **Xenia** is an independent project. Its [BSD-3-Clause license](https://github.com/xenia-project/xenia/blob/95a5c3ee2/LICENSE) allows redistribution with the required copyright, conditions, and disclaimer; other included dependencies retain their own terms. Native Boot Studio uses a user-selected official release and does not bundle it.
- **XexTool** is by xorloser. No express redistribution permission was verified for the inspected 6.3 tool. Obtain and supply it separately under the author's terms.
- **Microsoft Xbox software**, including `bootanim.xex`, remains subject to Microsoft's terms. Native Boot Studio's MIT license grants no rights to redistribute the original or a patched copy.

The public documentation uses only the editor's own preset-library UI, with no Xbox boot-screen capture. Detailed distribution notes in English and German are in the source repository under `docs/DISTRIBUTION.en.md` and `docs/DISTRIBUTION.de.md`.

Native Boot Studio is not affiliated with or endorsed by Microsoft, xorloser, or the Xenia project.
