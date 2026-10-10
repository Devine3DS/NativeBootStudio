# Native Boot Studio — Anleitung

## Einrichtung

Entpacke das vollständige Windows-Release in einen beschreibbaren Ordner. Starte `NativeBootStudio.exe`; Python muss nicht installiert sein. Oben kannst du Deutsch oder Englisch auswählen.

Das öffentliche Release enthält keine Microsoft-Bootdateien, kein XexTool und keinen Emulator. Beim ersten Start erklärt der Reiter **Dateien**, was du auswählen musst:

1. Deine eigene **unveränderte moderne `bootanim.xex` aus Dashboard/Kernel 17559**. Bereits umgefärbte Dateien und die klassische Animation werden als Ausgangsdatei nicht unterstützt.
2. Dein eigenes **XexTool 6.3** zum Lesen und Exportieren der XEX.
3. Optional **Xenia** für die native Shader-Vorschau. Lade die [getestete offizielle Windows-Version](https://github.com/xenia-project/release-builds-windows/releases/tag/v1.0.2844-master), entpacke den vollständigen Download separat und wähle `xenia.exe`. Die Vorschau benötigt einen passenden Windows-PC mit 64 Bit und einen Grafiktreiber mit Direct3D-12-Unterstützung.

Klicke auf **Eingabe erneut prüfen**. Der Export bleibt gesperrt, bis die Ausgangsdatei geprüft ist. Bestätigte Eingabe-/Toolpfade und der ausgewählte Xenia-Pfad werden in `settings.json` neben der EXE gespeichert.

Alternativ sind die Standardpfade `originals/modern/bootanim.xex`, `tools/xextool.exe` und `tools/preview/xenia.exe` neben der EXE möglich. Diese optionalen Ordner werden im öffentlichen Release nicht mitgeliefert. Gib eigene Dateien nur weiter, wenn ihre Bedingungen das ausdrücklich erlauben.

## Farbdesign erstellen

Wähle unter **Palette** eine Presetgruppe und ein Preset. Die Presets stimmen Hintergrund, Wirbel, Kugel-X, Leuchten, Highlights, Szenentönung und Schrift aufeinander ab. Die Hauptfarbe färbt zusammengehörige Elemente und erhält dabei deren Schattierung. Mit den einzelnen Farbreglern kannst du das Design weiter anpassen.

Unter **Details** und **Animation** findest du die unterstützten Größen-, Positions- und Timing-Einstellungen. Sie verändern die vorhandene Animation. Eigene Texte und frei erstellte Bewegungen werden nicht unterstützt. Native Kameraregler stehen nur dort bereit, wo sie in der echten Vorschau wirken. Modellregler sind im Shader-Modus ausgeblendet.

Prüfe Änderungen mit Originalvergleich und Rückgängig/Wiederholen. Bei Bedarf kannst du die Vorschauhilfe aufklappen. Änderungen können einen kurzen Neustart der Shader-Vorschau auslösen. Bootton und Systemübergabe werden ausgelassen; Emulation und verändertes Audiotiming müssen abschließend auf Hardware geprüft werden. Die Modellvorschau ist eine Annäherung und auch ohne Xenia verfügbar.

## Eigene Presets und Projekte

Öffne **Eigene Presets**, um die aktuellen Farben unter einem Namen zu speichern. Gespeicherte Presets kannst du anwenden, umbenennen, ersetzen, löschen oder exportieren. Geteilte `.nbpalette.json`-Dateien lassen sich dort importieren.

Farbpresets ändern weder Größe noch Position oder Animationsgeschwindigkeit. Die eingebauten Presets bleiben von deiner Bibliothek getrennt. Eigene Presets liegen im Ordner `UserPresets` neben der EXE. Sichere ihn vor einem Update.

Ein `.nbstudio.json`-Projekt speichert die umfassenderen Editoreinstellungen. Projekte können lokale Eingabe-/Toolpfade enthalten; prüfe sie vor dem Teilen. Teile Farbpreset-JSON statt originaler oder modifizierter Microsoft-XEX-Dateien.

## Export

Wähle beim Export von `bootanim.xex` das Ziel:

- **HDD:** erstellt eine Datei für einen nativen HDD-Lader. Mit `remap_bootanim_17559` liegt sie im Hauptverzeichnis der internen HDD als `Hdd:\bootanim.xex`; der Remap wird einmal ins NAND-Image eingebaut.
- **NAND:** erstellt eine Datei zum Ersetzen von `bootanim.xex` in einem neu gebauten NAND-Image, mit tatsächlichem CRC-32 und ohne HDD-Remap. Sie ist kein vollständiges NAND-Image.

Die enthaltene [Installationsanleitung](INSTALLATION.de.md) beschreibt beide Wege, den separaten Remap-Download, xeBuild-/J-Runner-Einrichtung, RGH3-Besonderheiten und direkten NAND-Ersatz. Im Windows-Release liegt sie unter `docs/INSTALLATION.de.md`.

Das Programm prüft die exportierte Datei und erzeugt einen Exportbericht. Es kopiert nichts auf die Konsole und flasht keinen NAND. Bewahre das Original und eine funktionierende Wiederherstellungssicherung auf. Die Exporte benötigen eine geeignete RGH/JTAG-Konsole; eine unveränderte Retail-Konsole kann sie nicht ausführen.

Geschwindigkeitsänderungen passen das ursprüngliche Audio nicht zeitlich an. Prüfe Darstellung, Timing und Bootverhalten abschließend auf deiner Konsole.

## Fehlerbehebung

| Problem | Prüfen |
| --- | --- |
| Export gesperrt | Original und XexTool auswählen, dann Eingabe prüfen. |
| Ausgangsdatei abgelehnt | Unterstütztes, unverändertes modernes 17559-Original verwenden. |
| Shader-Vorschau nicht verfügbar | Xenia auswählen und Windows-/GPU-Voraussetzungen prüfen. |
| Einstellungen/Presets nicht speicherbar | Programmordner an einen beschreibbaren Ort verschieben. |
| Presetname existiert bereits | Umbenennen oder das vorhandene Preset gezielt ersetzen. |

Lizenzhinweise stehen in `LICENSE` und `NOTICE.md` im Paket. Fremde Tools und Xbox-Dateien unterliegen ihren eigenen Bedingungen.
