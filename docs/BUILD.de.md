# Aus dem Quellcode bauen

Für die Windows-EXE werden **Windows mit 64 Bit und Python 3.13.7** verwendet. Die folgenden PowerShell-Befehle führst du im Hauptordner des Repositorys aus.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe src/studio.py
```

Pillow ist die Programmbibliothek. PyInstaller erstellt die EXE, Capstone unterstützt Integrationstests auf Befehlsebene, Black formatiert den Code. Ein Xbox-SDK wird nicht benötigt.

## Prüfen und verpacken

```powershell
.\.venv\Scripts\python.exe -m black --check src tests scripts
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/build_release.py --build
```

Der Packager erzeugt unter `dist/`:

- `NativeBootStudio-4.2.2-Windows-x64.zip`: EXE, deutsche/englische Benutzer- und Installationsanleitungen, CRC-32-Hilfe und Lizenzhinweise.
- `NativeBootStudio-4.2.2-source.zip`: bereinigter Quellcode, Tests, Dokumentation, Build-Skript und GitHub-Workflow.
- `SHA256SUMS.txt`: SHA-256-Prüfsummen beider Archive.

Temporäre Build-Dateien liegen unter `.build/`. Beide Ordner werden von Git ignoriert. Der Source-Packager verwendet festgelegte Datei-/Ordnerlisten. Binärdateien, Xbox-Dateien, persönliche Einstellungen, Projekte, Presets und private Testdateien werden nicht mitgenommen. Prüfe die Archivinhalte vor der Veröffentlichung.

Eine vorhandene EXE kannst du mit `python scripts/build_release.py --exe PFAD` verpacken. `--out PFAD` legt den Ausgabeordner fest.

## Optionale Integrationstests

Im öffentlichen Repository liegen keine Xbox-Dateien oder fremden EXE-Dateien. Tests, die Original-XEX und XexTool benötigen, werden ohne diese Dateien übersprungen. Die übrigen Tests laufen trotzdem. Für die vollständige Prüfung stellst du eigene Dateien **außerhalb des Repositorys** bereit:

```powershell
$env:NBS_BOOTANIM = 'C:\MyPrivateFiles\bootanim.xex'
$env:NBS_XEXTOOL = 'C:\MyPrivateTools\xextool.exe'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Benötigt wird das unterstützte unveränderte moderne 17559-Original. `NBS_XENIA` kann für manuelle Vorschauprüfungen auf deinen Emulator zeigen. In der Anwendung kannst du die Pfade auch im Reiter Dateien auswählen.

GitHub Actions prüft die Formatierung, führt die öffentlichen Tests aus, baut unter Windows und lädt Artefakte hoch. Ein GitHub-Release wird **nicht** automatisch veröffentlicht. Das Bootverhalten auf Hardware muss weiterhin auf der Konsole geprüft werden.

## Lizenzhinweise der Abhängigkeiten

Die mitgelieferten Laufzeithinweise passen zu Python 3.13, Pillow 11.3.0, PyInstaller 6.20.0 und packaging 26.2 dieses Releases. Bei Änderungen an Laufzeitabhängigkeiten müssen die Hinweise unter `licenses/runtime/` und die Inhalte der fertigen EXE geprüft werden. Xenia, XexTool und Microsoft-Binärdateien werden vom Build-Skript nie hinzugefügt. Siehe [Weitergabe und Lizenzen](DISTRIBUTION.de.md).
