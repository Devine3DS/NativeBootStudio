# Changelog

## 4.2.2 — Private file paths

- File setup shows filenames only, without Windows usernames or folder paths.
- Unconfigured or missing files show a translated "No file selected" label.
- Original file locations remain available internally for preview, export, and saved local settings.
- English/German landing pages now contain the complete user tutorial, including HDD and NAND installation.

## 4.2.1 — Public packaging

- Clean source repository and minimal Windows release, without Xbox files, XexTool, or Xenia.
- User-supplied input/tool/emulator selection, remembered paths, and usable first-run setup.
- English/German user, build, publishing, and distribution guides; dependency notices.
- English/German installation guides for the 17559 HDD remap and direct NAND image replacement, with a CRC-32 helper.
- Formatted source in `src/`, tests in `tests/`, explicit archive allowlists, and Windows CI.
- Removed the obsolete standalone color-editor GUI and private workspace fallback paths.

## 4.2 — Preset library and interface

- Save/apply/rename/replace/delete/import/export custom color presets.
- Cleaner dark interface, compact header, larger preview, and collapsible preview help.
- Removed redundant preset shortcut buttons; hid model-only controls in shader preview.

## 4.1 — Native shader preview

- Preview the original modern animation renderer through Xenia.
- Playback/timeline/original comparison; classic boot animation removed from supported inputs.
