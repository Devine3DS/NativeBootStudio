# Eine exportierte Bootanimation installieren

[English](INSTALLATION.en.md)

Für eine unterstützte **17559-RGH/JTAG-Konsole** stehen zwei Wege zur Verfügung:

| Weg | Exportziel im Studio | Ablage der Animation | Änderung am NAND |
| --- | --- | --- | --- |
| HDD mit Remap | **HDD** | Hauptverzeichnis der internen HDD: `Hdd:\bootanim.xex` | 17559-Remap einmal in das Image einbauen. |
| Direkt im NAND ersetzen | **NAND** | Flash-Dateisystem des NAND-Images als `bootanim.xex` | Image mit eigener Datei neu bauen; Remap weglassen. |

Native Boot Studio erstellt XEX und Exportbericht. Das NAND-Image wird separat gebaut und geflasht. Sichere vorher den funktionierenden NAND-Dump, CPU-Key, die originale Bootdatei und deine Builder-Einstellungen. Verwende die für deine Konsole bereits geprüften Mainboard-/NAND-/Hack-Einstellungen. Corona mit 4-GB-eMMC und 16-MB-NAND benötigen jeweils passende Flashverfahren.

## Möglichkeit A — HDD mit remap_bootanim_17559

Im [Release von Xbox360BootAnimationCreator](https://github.com/TheOnlyLordVirus/Xbox360BootAnimationCreator/releases/tag/Release) liegt `remap_bootanim_17559.bin`, dort **Mena** zugeschrieben. Wir verwenden den dokumentierten HDD-Installationsweg dieses Patches; die Animation erstellt weiterhin Native Boot Studio. Der Patch wird separat heruntergeladen und liegt unserem Release nicht bei.

1. Exportiere dein Theme im Studio mit Ziel **HDD** als `bootanim.xex`.
2. Sichere eine vorhandene HDD-Bootdatei und kopiere den Export ins **Hauptverzeichnis der internen Festplatte**. Dateimanager zeigen es üblicherweise als `Hdd:\bootanim.xex` oder `Hdd1:\bootanim.xex`. USB-Laufwerke oder Unterordner sind nicht das dokumentierte Ziel dieses Remaps.
3. Ist genau dieser Remap bereits eingerichtet und lädt von dort, brauchst du für ein neues Theme kein neues NAND-Image: HDD-Datei ersetzen und neu starten.
4. Andernfalls lade beim verlinkten Release **nur die Remap-Datei** herunter. Lege sie in deiner separaten xeBuild-/J-Runner-Installation unter `xeBuild\17559\bin\remap_bootanim_17559.bin` ab.
5. Lade deinen eigenen NAND und CPU-Key im Image-Builder und behalte die richtigen Mainboard-/Hack-Einstellungen bei. Ergänze beim Bauen diesen Patchparameter:

   ```text
   -a remap_bootanim_17559
   ```

   Der Parameter nennt den Patch **ohne `.bin`**. Der übrige funktionierende Build-Befehl und notwendige RGH3-Konvertierungsschritte bleiben erhalten. Das Xenon-/JTAG-Beispiel des Release-Autors ist kein passender Befehl für eine Corona mit RGH3.
6. In J-Runner with Extras lassen sich eigene Befehle unter **Advanced → XeBuild Command…** eingeben. Dort kommen nur xeBuild-Parameter hinein, nicht `xeBuild.exe`. J-Runner ergänzt Daten-/Ausgabepfade selbst; `-d` und den Ausgabedateinamen weglassen. Übernimm alle relevanten Parameter deines vorhandenen Setups. **Bei RGH3 darfst du nicht voraussetzen, dass dieser Custom-Command-Weg die normale automatische RGH3-Nachkonvertierung ausführt. Lade das gebaute Image als Source und konvertiere es vor dem Flashen über Advanced → Convert to RGH3 mit korrektem Mainboard/CPU-Key und deinen bewährten Einstellungen.**
7. Prüfe im erfolgreichen Build-Log den Remap und stelle sicher, dass das fertige Image zu deiner Konsole und ihrem Hacktyp passt. Flashe das vollständige Image mit dem passenden Verfahren für dein Mainboard/NAND und starte mit angeschlossener interner HDD neu.

Nach der Einrichtung genügt für weitere Farbänderungen ein neuer **HDD**-Export und das Ersetzen von `Hdd:\bootanim.xex`. Verlasse dich nicht darauf, dass der Remap bei fehlender HDD/Datei auf die NAND-Animation zurückfällt.

## Möglichkeit B — bootanim.xex in einem neu gebauten NAND-Image ersetzen

Hier bleibt die Animation im NAND. Dieser Weg benötigt den normalen NAND-Bootpfad **ohne `remap_bootanim_17559`**. Ein Austausch der NAND-Datei wirkt nicht, solange der Kernel weiterhin auf die HDD umleitet.

1. Exportiere im Studio mit Ziel **NAND** als `bootanim.xex`.
2. Arbeite in einer gesicherten Kopie deiner xeBuild-/J-Runner-Installation. Lade deinen NAND-Dump/CPU-Key und wähle deine korrekten Konsoleneinstellungen sowie Dashboard **17559**.
3. Lege die exportierte XEX in dieser Builder-Kopie unter `xeBuild\17559\bootanim.xex` ab.
4. Ermittle die tatsächlich verwendete Firmware-INI. Bei einem normalen 17559-Glitch2-Build ist es `xeBuild\17559\_glitch2.ini`, bei JTAG `_jtag.ini`. Andere Buildprofile können andere INIs verwenden; prüfe das Build-Log.
5. Ändere in deren Abschnitt `[flashfs]` ausschließlich den CRC-32-Wert des Eintrags `bootanim.xex` auf den Wert **deines exportierten NAND-Files**. Alle übrigen Einträge und Abschnitte bleiben erhalten. Das Format lautet:

   ```ini
   bootanim.xex,DEIN_8_STELLIGER_CRC32
   ```

   `DEIN_8_STELLIGER_CRC32` ist ein Platzhalter und darf nicht so übernommen werden. Das mitgelieferte Hilfsskript berechnet den Wert in PowerShell, ohne die Datei zu verändern:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\crc32.ps1 -Path 'C:\MyExports\bootanim.xex'
   ```

   Starte den Befehl im entpackten Programm-/Source-Hauptordner. Der Execution-Policy-Parameter gilt nur für diesen Hilfsskript-Prozess. Übernimm die acht ausgegebenen Hex-Zeichen in die INI. CRC-32 ist nicht die SHA-256-Prüfsumme aus dem Studio-Bericht. Berechne ihn nach jedem neuen Export erneut.
6. Baue das NAND-Image mit deinem normalen Ablauf inklusive notwendiger RGH3-Schritte und **ohne den Remapparameter**. Kontrolliere, dass das Log deine Ersatzdatei mit passendem CRC verwendet und der Build erfolgreich endet. Wird das Original verwendet, ein CRC-Fehler gemeldet oder reicht der Flash-Dateisystemplatz nicht, nicht flashen; korrigiere zuerst Eingabe und Buildprofil.
7. Stelle danach Original-INI und ursprüngliche Builder-Datei wieder her, damit spätere Images das Theme nicht versehentlich übernehmen. Prüfe das fertige Image für deine Konsole, flashe es mit deinem passenden Verfahren und starte neu.

Ersetzt wird die Datei in einem neu gebauten NAND-**Image**. Keine vermeintlichen Raw-Offsets im Dump mit einem Hexeditor ändern und nicht die laufende `Flash:`-/`SFC:`-Bootdatei im Dashboard-Dateimanager löschen, um den Dateisystem-Neubau zu umgehen.

## Zwischen den Wegen wechseln und Ergebnis prüfen

- **HDD → NAND:** Image ohne Remap bauen und den NAND-Export mit passendem CRC einbauen. Eine vorhandene HDD-Datei zu behalten beendet die Kernelumleitung nicht.
- **NAND → HDD:** HDD-Export verwenden und Remap wie in Möglichkeit A einbauen.
- Erscheint weiterhin das Original, prüfe zuerst tatsächlichen Bootpfad, Exportziel, aktive Firmware-INI, Build-Log und Dateinamen, bevor du erneut Farben änderst.

Die Anleitung basiert auf dem Remap-Release, J-Runners Befehlsverarbeitung und seiner 17559-Firmwarekonfiguration. Die lokalen Tests prüfen den XEX-Export des Studios, nicht NAND-Flashen oder den Patch auf jedem Mainboard. Vor dem Flashen muss eine funktionierende Wiederherstellungsmöglichkeit vorhanden sein.

Quellen: [Remap-Anleitung und Download](https://github.com/TheOnlyLordVirus/Xbox360BootAnimationCreator/releases/tag/Release), [J-Runner-Quellcode](https://github.com/Octal450/J-Runner-with-Extras) und das in dessen README verlinkte offizielle Paket (17559-Firmware-INI/Readme). Fremde Dateien unterliegen ihren eigenen Lizenzbedingungen.
